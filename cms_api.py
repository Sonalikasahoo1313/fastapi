from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import os
import shutil
import traceback
from db_connection import get_global_tiffin_db_connection

router = APIRouter()

BASE_UPLOAD_FOLDER = "uploads"
RESOURCE_FOLDER = os.path.join(BASE_UPLOAD_FOLDER, "cms_resource")
os.makedirs(RESOURCE_FOLDER, exist_ok=True)

# CMS ID Generator
def generate_cms_id(cursor):
    cursor.execute("SELECT id FROM cms ORDER BY id DESC LIMIT 1")
    last = cursor.fetchone()
    if last and 'id' in last:
        try:
            last_num = int(last['id'][3:]) if last['id'][3:].isdigit() else 0
        except Exception as e:
            print("DEBUG: Error parsing last id:", last['id'], e)
            last_num = 0
        new_num = last_num + 1
    else:
        new_num = 1
    return f"cms{new_num:04d}"

# -------------------- ADD CMS --------------------
@router.post("/cms/add")
def add_cms(
    title: str = Form(...),
    short_description: Optional[str] = Form(None),
    long_description: Optional[str] = Form(None),
    mediafile: Optional[UploadFile] = File(None),
    created_by: Optional[str] = Form(None)
):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cms_id = generate_cms_id(cursor)
        original_filename = None
        media_url = None

        if mediafile and mediafile.filename:
            original_filename = mediafile.filename
            ext = original_filename.split('.')[-1]
            renamed_file = f"{cms_id}.{ext}"
            renamed_path = os.path.join(RESOURCE_FOLDER, renamed_file)
            with open(renamed_path, "wb") as f:
                shutil.copyfileobj(mediafile.file, f)
            media_url = f"/uploads/cms_resource/{renamed_file}"

        insert_query = """
            INSERT INTO cms (
                id, title, short_description, long_description,
                mediafile, remarks, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            cms_id, title, short_description, long_description,
            media_url, original_filename, created_by
        )

        cursor.execute(insert_query, values)
        db.commit()

        return {
            "message": "CMS entry added successfully.",
            "cms_id": cms_id,
            "media_url": media_url,
            "original_filename": original_filename
        }

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# -------------------- FETCH ALL CMS --------------------
@router.get("/cms/all")
def fetch_all_cms():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("""
            SELECT id, title, short_description, long_description, 
                   mediafile, remarks, created_on, created_by, updated_on, updated_by
            FROM cms ORDER BY id DESC
        """)
        data = cursor.fetchall()
        return {"cms_entries": data}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# -------------------- FETCH CMS BY ID --------------------
@router.get("/cms/{cms_id}")
def fetch_cms_by_id(cms_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("""
            SELECT id, title, short_description, long_description,
                   mediafile, remarks, created_on, created_by, updated_on, updated_by
            FROM cms WHERE id = %s
        """, (cms_id,))
        data = cursor.fetchone()
        if not data:
            raise HTTPException(status_code=404, detail="CMS entry not found")
        return data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# -------------------- UPDATE CMS --------------------
@router.put("/cms/update/{cms_id}")
def update_cms(
    cms_id: str,
    title: str = Form(...),
    short_description: Optional[str] = Form(None),
    long_description: Optional[str] = Form(None),
    mediafile: Optional[UploadFile] = File(None),
    updated_by: Optional[str] = Form(None)
):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT mediafile, remarks FROM cms WHERE id = %s", (cms_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="CMS entry not found")

        old_url = row["mediafile"]
        old_remarks = row["remarks"]
        new_media_url = old_url
        remarks = old_remarks

        if mediafile and mediafile.filename:
            ext = mediafile.filename.split('.')[-1]
            renamed_file = f"{cms_id}.{ext}"
            renamed_path = os.path.join(RESOURCE_FOLDER, renamed_file)

            with open(renamed_path, "wb") as f:
                shutil.copyfileobj(mediafile.file, f)

            # remove old file if different
            if old_url and renamed_file not in old_url:
                old_path = os.path.join(BASE_UPLOAD_FOLDER, old_url.replace("/uploads/", ""))
                if os.path.exists(old_path):
                    os.remove(old_path)

            new_media_url = f"/uploads/cms_resource/{renamed_file}"
            remarks = mediafile.filename

        update_query = """
            UPDATE cms SET title=%s, short_description=%s, long_description=%s,
                mediafile=%s, remarks=%s, updated_by=%s
            WHERE id=%s
        """
        cursor.execute(update_query, (
            title, short_description, long_description,
            new_media_url, remarks, updated_by, cms_id
        ))

        db.commit()
        return {"message": "CMS entry updated successfully."}

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# -------------------- DELETE CMS --------------------
@router.delete("/cms/delete/{cms_id}")
def delete_cms(cms_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT mediafile FROM cms WHERE id = %s", (cms_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="CMS entry not found")

        media_url = row["mediafile"]
        if media_url:
            local_path = os.path.join(BASE_UPLOAD_FOLDER, media_url.replace("/uploads/", ""))
            if os.path.exists(local_path):
                os.remove(local_path)

        cursor.execute("DELETE FROM cms WHERE id = %s", (cms_id,))
        db.commit()

        return {"message": f"CMS entry '{cms_id}' deleted successfully."}

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
