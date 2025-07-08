from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from typing import Optional
import os
from db_connection import get_global_tiffin_db_connection

router = APIRouter()

UPLOAD_FOLDER = "uploads/about_us_resource"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------- Generate content_id -------------------
def generate_content_id(cursor):
    cursor.execute("SELECT content_id FROM aboutus_howitworks ORDER BY content_id DESC LIMIT 1")
    row = cursor.fetchone()
    if row and row["content_id"]:
        last_id = int(row["content_id"].replace("content", ""))
        new_id = f"content{last_id + 1:07d}"
    else:
        new_id = "content0000001"
    return new_id

# ------------------- ADD -------------------
@router.post("/aboutus_howitworks/")
async def add_howit_item(
    image: Optional[UploadFile] = File(None),
    icon: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    created_by: Optional[str] = Form(None)
):
    db, cursor = get_global_tiffin_db_connection()
    content_id = generate_content_id(cursor)

    image_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        image_filename = f"{content_id}{ext}"
        image_path = f"/uploads/about_us_resource/{image_filename}"
        file_path = os.path.join(UPLOAD_FOLDER, image_filename)

        with open(file_path, "wb") as f:
            f.write(await image.read())

    try:
        sql = """
            INSERT INTO aboutus_howitworks
            (content_id, image, icon, title, text, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (content_id, image_path, icon, title, text, created_by))
        db.commit()
        return {"message": "Item added", "content_id": content_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ------------------- FETCH ALL -------------------
@router.get("/aboutus_howitworks/")
def fetch_all_howit_items():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM aboutus_howitworks ORDER BY content_id DESC")
        return cursor.fetchall()
    finally:
        db.close()

# ------------------- UPDATE -------------------
@router.put("/aboutus_howitworks/{content_id}")
async def update_howit_item(
    content_id: str,
    image: Optional[UploadFile] = File(None),
    icon: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    updated_by: Optional[str] = Form(None)
):
    db, cursor = get_global_tiffin_db_connection()

    cursor.execute("SELECT * FROM aboutus_howitworks WHERE content_id = %s", (content_id,))
    existing = cursor.fetchone()
    if not existing:
        db.close()
        raise HTTPException(status_code=404, detail="Item not found")

    image_path = existing["image"]
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        image_filename = f"{content_id}{ext}"
        image_path = f"/uploads/about_us_resource/{image_filename}"
        file_path = os.path.join(UPLOAD_FOLDER, image_filename)

        with open(file_path, "wb") as f:
            f.write(await image.read())

        # Remove old image
        old_path = existing["image"]
        if old_path:
            local_path = old_path.replace("/uploads", "uploads")
            if os.path.exists(local_path):
                os.remove(local_path)

    sql = "UPDATE aboutus_howitworks SET "
    fields = []
    values = []

    if image:
        fields.append("image = %s")
        values.append(image_path)
    if icon is not None:
        fields.append("icon = %s")
        values.append(icon)
    if title is not None:
        fields.append("title = %s")
        values.append(title)
    if text is not None:
        fields.append("text = %s")
        values.append(text)
    if updated_by is not None:
        fields.append("updated_by = %s")
        values.append(updated_by)

    if not fields:
        db.close()
        return {"message": "No update fields provided"}

    sql += ", ".join(fields) + " WHERE content_id = %s"
    values.append(content_id)

    try:
        cursor.execute(sql, tuple(values))
        db.commit()
        return {"message": "Item updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ------------------- DELETE -------------------
@router.delete("/aboutus_howitworks/{content_id}")
def delete_howit_item(content_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT image FROM aboutus_howitworks WHERE content_id = %s", (content_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")

        image_path = row["image"]
        if image_path:
            local_path = image_path.replace("/uploads", "uploads")
            if os.path.exists(local_path):
                os.remove(local_path)

        cursor.execute("DELETE FROM aboutus_howitworks WHERE content_id = %s", (content_id,))
        db.commit()
        return {"message": "Item and image deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
