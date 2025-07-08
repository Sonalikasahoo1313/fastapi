from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
import bcrypt
import os
from datetime import datetime
from typing import Optional
import uuid
from db_connection import get_global_tiffin_db_connection, get_vault_db_connection

router = APIRouter()
UPLOAD_FOLDER = "uploads/admin_profile"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def generate_admin_id(cursor):
    cursor.execute("SELECT admin_id FROM admin_login ORDER BY admin_id DESC LIMIT 1")
    row = cursor.fetchone()
    if row and row["admin_id"]:
        last_id = int(row["admin_id"].replace("admin", ""))
        return f"admin{last_id + 1:07d}"
    return "admin0000001"

# -------------------- Register --------------------
@router.post("/admin/register")
def register_admin(
    fname: str = Form(...),
    lname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    dob: str = Form(...),
    phone_number: str = Form(...),
    country: str = Form(...),
    city: str = Form(...),
    pincode: str = Form(...),
    created_by: str = Form(...),
    status: str = Form("active"),
    photo: UploadFile = File(None)
):
    db, cursor = get_global_tiffin_db_connection()
    relative_path = None

    if photo and photo.filename:
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            ext = os.path.splitext(photo.filename)[1]
            filename = f"{fname}_{timestamp}{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(file_path, "wb") as f:
                f.write(photo.file.read())
            relative_path = f"/uploads/admin_profile/{filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File upload error: {str(e)}")

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    admin_id = generate_admin_id(cursor)

    query = """
        INSERT INTO admin_login 
        (admin_id, fname, lname, email, password, role, dob, phone_number, country, city, pincode, photo, status, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        admin_id, fname, lname, email, hashed_password, role, dob, phone_number,
        country, city, pincode, relative_path, status, created_by
    )

    try:
        cursor.execute(query, values)
        db.commit()
        return {
            "message": "Admin registered successfully",
            "admin_id": admin_id,
            "photo_url": relative_path
        }
    except Exception as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {err}")
    finally:
        db.close()

# -------------------- Login --------------------
@router.post("/admin/login")
def login_admin(email: str = Form(...), password: str = Form(...)):
    vault_db, vault_cursor = get_vault_db_connection()
    db, cursor = get_global_tiffin_db_connection()

    vault_cursor.execute("SELECT * FROM vault_users WHERE email = %s", (email,))
    user = vault_cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in vault.")

    if user['status'].lower() != "active":
        raise HTTPException(status_code=403, detail="Access denied. Please contact the administrator.")

    cursor.execute("SELECT * FROM admin_login WHERE email = %s", (email,))
    admin = cursor.fetchone()

    if not admin or not bcrypt.checkpw(password.encode('utf-8'), admin['password'].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if admin['status'].lower() != "active":
        raise HTTPException(status_code=403, detail="Your request has been denied. Please contact the administrator.")

    del admin['password']
    return {"message": "Login successful", "admin": admin}

# -------------------- Get All Admins --------------------
@router.get("/admin/all")
def get_all_admins():
    db, cursor = get_global_tiffin_db_connection()
    cursor.execute("""
        SELECT admin_id, fname, lname, email, role, dob, phone_number, country, city, pincode, photo, status 
        FROM admin_login
    """)
    admins = cursor.fetchall()
    db.close()
    return {"data": admins}

# -------------------- Get Admin by Email --------------------
@router.get("/admin/{email}")
def get_admin_by_email(email: str):
    db, cursor = get_global_tiffin_db_connection()
    cursor.execute("""
        SELECT admin_id, fname, lname, email, role, dob, phone_number, country, city, pincode, photo, status 
        FROM admin_login WHERE email = %s
    """, (email,))
    admin = cursor.fetchone()
    db.close()

    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return admin

# -------------------- Delete Admin --------------------
@router.delete("/admin/{email}")
def delete_admin(email: str):
    db, cursor = get_global_tiffin_db_connection()
    cursor.execute("SELECT photo FROM admin_login WHERE email = %s", (email,))
    result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Admin not found")

    photo_path = result['photo']
    local_path = photo_path.replace("/uploads", "uploads") if photo_path else None

    try:
        cursor.execute("DELETE FROM admin_login WHERE email = %s", (email,))
        db.commit()
        if local_path and os.path.exists(local_path):
            os.remove(local_path)
        return {"message": "Admin deleted successfully and profile photo removed (if existed)."}
    except Exception as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {err}")
    finally:
        db.close()

# -------------------- Update Admin --------------------
@router.put("/admin/update/{admin_id}")
def update_admin_with_photo(
    admin_id: str,
    updated_by: str = Form(...),
    fname: Optional[str] = Form(None),
    lname: Optional[str] = Form(None),
    dob: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    pincode: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None)
):
    db, cursor = get_global_tiffin_db_connection()
    update_fields = {}

    if fname: update_fields['fname'] = fname
    if lname: update_fields['lname'] = lname
    if dob: update_fields['dob'] = dob
    if phone_number: update_fields['phone_number'] = phone_number
    if country: update_fields['country'] = country
    if city: update_fields['city'] = city
    if pincode: update_fields['pincode'] = pincode
    if role: update_fields['role'] = role
    if status: update_fields['status'] = status

    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[-1]
        unique_suffix = uuid.uuid4().hex[:6]
        filename = f"{admin_id}_{unique_suffix}{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(file_path, "wb") as f:
            f.write(photo.file.read())
        update_fields['photo'] = f"/uploads/admin_profile/{filename}"

    update_fields['updated_by'] = updated_by

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    set_clause = ", ".join([f"{key} = %s" for key in update_fields])
    values = list(update_fields.values()) + [admin_id]

    try:
        cursor.execute(f"UPDATE admin_login SET {set_clause} WHERE admin_id = %s", values)
        db.commit()
        return {"message": "Admin updated successfully"}
    except Exception as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {err}")
    finally:
        db.close()

# -------------------- Change Password --------------------
@router.put("/admin/{email}/change-password")
def change_password(email: str, old_password: str = Form(...), new_password: str = Form(...)):
    db, cursor = get_global_tiffin_db_connection()
    cursor.execute("SELECT password FROM admin_login WHERE email = %s", (email,))
    admin = cursor.fetchone()

    if not admin:
        db.close()
        raise HTTPException(status_code=404, detail="Admin not found")

    if not bcrypt.checkpw(old_password.encode('utf-8'), admin['password'].encode('utf-8')):
        db.close()
        raise HTTPException(status_code=401, detail="Old password is incorrect")

    hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        cursor.execute("UPDATE admin_login SET password = %s WHERE email = %s", (hashed_new_password, email))
        db.commit()
        return {"message": "Password updated successfully"}
    except Exception as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {err}")
    finally:
        db.close()
