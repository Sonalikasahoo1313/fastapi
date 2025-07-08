from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from db_connection import get_global_tiffin_db_connection
import os
import shutil
import uuid

router = APIRouter()

UPLOAD_DIR = "uploads/contact_us_resource"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------- ADD CONTACT ---------------------
@router.post("/contact/add")
async def add_contact(
    image: UploadFile = File(None),
    title: str = Form(None),
    short_description: str = Form(None),
    long_description: str = Form(None),
    icon: str = Form(None),
    created_by: str = Form(None)
):
    db, cursor = get_global_tiffin_db_connection()
    image_url = None

    try:
        if image and image.filename:
            ext = os.path.splitext(image.filename)[-1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(UPLOAD_DIR, unique_name)
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_url = f"/uploads/contact_us_resource/{unique_name}"

        query = """
            INSERT INTO contact_us (
                image, title, short_description, long_description, icon, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = [image_url, title, short_description, long_description, icon, created_by]
        cursor.execute(query, values)
        db.commit()

        return {"message": "Contact added successfully", "image_url": image_url}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()

# --------------------- FETCH ALL ---------------------
@router.get("/contact/all")
def fetch_all_contacts():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM contact_us")
        return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# --------------------- UPDATE ALL CONTACTS ---------------------
@router.put("/contact/update_all")
async def update_all_contacts(
    image: UploadFile = File(None),
    title: str = Form(None),
    short_description: str = Form(None),
    long_description: str = Form(None),
    icon: str = Form(None),
    updated_by: str = Form(None)
):
    db, cursor = get_global_tiffin_db_connection()
    image_url = None

    try:
        # Get old image path to delete
        cursor.execute("SELECT image FROM contact_us")
        old_images = cursor.fetchall()

        if image and image.filename:
            ext = os.path.splitext(image.filename)[-1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(UPLOAD_DIR, unique_name)
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_url = f"/uploads/contact_us_resource/{unique_name}"

            # Remove old images
            for img in old_images:
                if img["image"]:
                    old_path = os.path.join("uploads", img["image"].replace("/uploads/", ""))
                    if os.path.exists(old_path):
                        os.remove(old_path)

        query = """
            UPDATE contact_us SET
                image = %s,
                title = %s,
                short_description = %s,
                long_description = %s,
                icon = %s,
                updated_by = %s
        """
        values = [image_url, title, short_description, long_description, icon, updated_by]
        cursor.execute(query, values)
        db.commit()

        return {"message": "All contact records updated successfully", "image_url": image_url}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# --------------------- DELETE ALL CONTACTS ---------------------
@router.delete("/contact/delete_all")
def delete_all_contacts():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT image FROM contact_us")
        images = cursor.fetchall()

        for img in images:
            if img["image"]:
                local_path = os.path.join("uploads", img["image"].replace("/uploads/", ""))
                if os.path.exists(local_path):
                    os.remove(local_path)

        cursor.execute("DELETE FROM contact_us")
        db.commit()

        return {"message": "All contact records deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
