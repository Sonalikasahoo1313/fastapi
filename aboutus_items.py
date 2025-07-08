from fastapi import APIRouter, File, Form, UploadFile, HTTPException
import os
from typing import Optional
from db_connection import get_global_tiffin_db_connection

router = APIRouter()

UPLOAD_FOLDER = "uploads/about_us_resource"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------- Generate ID -------------------
def generate_content_id(cursor):
    cursor.execute("SELECT content_id FROM aboutus_items ORDER BY content_id DESC LIMIT 1")
    row = cursor.fetchone()
    if row and row["content_id"]:
        last_id = int(row["content_id"].replace("content", ""))
        return f"content{last_id + 1:07d}"
    return "content0000001"

# ------------- ADD -------------------
@router.post("/aboutus_items/")
async def add_aboutus_item(
    image: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    heading: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    button: Optional[str] = Form(None),
    created_by: Optional[str] = Form(None)
):
    db, cursor = get_global_tiffin_db_connection()
    content_id = generate_content_id(cursor)

    relative_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"{content_id}{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        relative_path = f"/uploads/about_us_resource/{filename}"

        with open(file_path, "wb") as f:
            f.write(await image.read())

    try:
        cursor.execute("""
            INSERT INTO aboutus_items (content_id, image, title, heading, text, contact, button, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            content_id, relative_path, title, heading, text, contact, button, created_by
        ))
        db.commit()
        return {"message": "Item added", "content_id": content_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ------------- FETCH ALL -------------------
@router.get("/aboutus_items/")
def fetch_all_items():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM aboutus_items ORDER BY content_id DESC")
        return {"data": cursor.fetchall()}
    finally:
        db.close()

# ------------- UPDATE -------------------
@router.put("/aboutus_items/{content_id}")
async def update_aboutus_item(
    content_id: str,
    image: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    heading: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    button: Optional[str] = Form(None),
    updated_by: Optional[str] = Form(None)
):
    db, cursor = get_global_tiffin_db_connection()
    cursor.execute("SELECT * FROM aboutus_items WHERE content_id = %s", (content_id,))
    existing = cursor.fetchone()

    if not existing:
        db.close()
        raise HTTPException(status_code=404, detail="Item not found")

    image_path = existing["image"]
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"{content_id}{ext}"
        image_path = f"/uploads/about_us_resource/{filename}"
        local_path = os.path.join("uploads/about_us_resource", filename)

        with open(local_path, "wb") as f:
            f.write(await image.read())

        # Delete old image
        old_path = existing["image"]
        if old_path:
            old_local_path = old_path.replace("/uploads", "uploads")
            if os.path.exists(old_local_path):
                os.remove(old_local_path)

    fields = []
    values = []

    if image:
        fields.append("image = %s")
        values.append(image_path)
    if title is not None:
        fields.append("title = %s")
        values.append(title)
    if heading is not None:
        fields.append("heading = %s")
        values.append(heading)
    if text is not None:
        fields.append("text = %s")
        values.append(text)
    if contact is not None:
        fields.append("contact = %s")
        values.append(contact)
    if button is not None:
        fields.append("button = %s")
        values.append(button)
    if updated_by is not None:
        fields.append("updated_by = %s")
        values.append(updated_by)

    if not fields:
        db.close()
        return {"message": "No update data provided"}

    update_query = f"UPDATE aboutus_items SET {', '.join(fields)} WHERE content_id = %s"
    values.append(content_id)

    try:
        cursor.execute(update_query, tuple(values))
        db.commit()
        return {"message": "Item updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ------------- DELETE -------------------
@router.delete("/aboutus_items/{content_id}")
def delete_aboutus_item(content_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT image FROM aboutus_items WHERE content_id = %s", (content_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")

        image_path = row["image"]
        if image_path:
            local_path = image_path.replace("/uploads", "uploads")
            if os.path.exists(local_path):
                os.remove(local_path)

        cursor.execute("DELETE FROM aboutus_items WHERE content_id = %s", (content_id,))
        db.commit()
        return {"message": "Item and associated image deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
