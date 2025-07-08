from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from db_connection import get_global_tiffin_db_connection
import os
import shutil
from uuid import uuid4

router = APIRouter()

UPLOAD_FOLDER = "uploads/gallery_resource"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- Generate new gallery_id ----------------
def generate_gallery_id(cursor):
    cursor.execute("SELECT gallery_id FROM gallery ORDER BY gallery_id DESC LIMIT 1")
    last_id = cursor.fetchone()

    if last_id and last_id["gallery_id"].startswith("gallery"):
        num = int(last_id["gallery_id"].replace("gallery", ""))
        new_num = num + 1
    else:
        new_num = 1

    return f"gallery{new_num:07d}"

# ---------------- Add Gallery ----------------
@router.post("/gallery/add")
async def add_gallery(
    heading: str = Form(...),
    subheading: str = Form(...),
    image_name: str = Form(...),
    created_by: str = Form(...),
    image: UploadFile = File(None)
):
    db, cursor = get_global_tiffin_db_connection()
    try:
        gallery_id = generate_gallery_id(cursor)
        media_path = None

        if image and image.filename.strip() != "":
            ext = image.filename.split('.')[-1]
            suffix = uuid4().hex[:8]
            filename = f"{gallery_id}_{suffix}.{ext}"

            file_path = os.path.join(UPLOAD_FOLDER, filename)
            media_path = f"/uploads/gallery_resource/{filename}"

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

        sql = """
            INSERT INTO gallery (
                gallery_id, heading, subheading, image, image_name, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (gallery_id, heading, subheading, media_path, image_name, created_by))
        db.commit()

        return {"message": "Gallery item added successfully", "gallery_id": gallery_id}
    finally:
        db.close()

# ---------------- Fetch All ----------------
@router.get("/gallery/fetch_all")
def fetch_all_gallery():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM gallery ORDER BY gallery_id DESC")
        records = cursor.fetchall()
        return {"data": records}
    finally:
        db.close()

# ---------------- Update Gallery ----------------
@router.put("/gallery/update/{gallery_id}")
async def update_gallery(
    gallery_id: str,
    heading: str = Form(...),
    subheading: str = Form(...),
    image_name: str = Form(...),
    updated_by: str = Form(...),
    image: UploadFile = File(None)
):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM gallery WHERE gallery_id = %s", (gallery_id,))
        existing = cursor.fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Gallery ID not found")

        media_path = existing["image"]

        if image and image.filename.strip() != "":
            ext = image.filename.split('.')[-1]
            suffix = uuid4().hex[:8]
            filename = f"{gallery_id}_{suffix}.{ext}"

            file_path = os.path.join(UPLOAD_FOLDER, filename)
            media_path = f"/uploads/gallery_resource/{filename}"

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

            # Delete old image
            old_path = existing["image"]
            if old_path and os.path.exists(old_path.replace("/uploads", "uploads")):
                os.remove(old_path.replace("/uploads", "uploads"))

        sql = """
            UPDATE gallery
            SET heading=%s, subheading=%s, image=%s, image_name=%s, updated_by=%s
            WHERE gallery_id=%s
        """
        cursor.execute(sql, (heading, subheading, media_path, image_name, updated_by, gallery_id))
        db.commit()

        return {"message": "Gallery item updated successfully"}
    finally:
        db.close()

# ---------------- Delete Gallery ----------------
@router.delete("/gallery/delete/{gallery_id}")
def delete_gallery(gallery_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM gallery WHERE gallery_id = %s", (gallery_id,))
        record = cursor.fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="Gallery ID not found")

        image_path = record["image"]
        if image_path and os.path.exists(image_path.replace("/uploads", "uploads")):
            try:
                os.remove(image_path.replace("/uploads", "uploads"))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error deleting image file: {str(e)}")

        cursor.execute("DELETE FROM gallery WHERE gallery_id = %s", (gallery_id,))
        db.commit()

        return {"message": f"Gallery item '{gallery_id}' deleted successfully and associated image removed."}
    finally:
        db.close()
