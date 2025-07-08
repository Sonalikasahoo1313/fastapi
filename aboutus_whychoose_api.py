from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from typing import Optional
import os
from db_connection import get_global_tiffin_db_connection

router = APIRouter()

UPLOAD_FOLDER = "uploads/about_us_resource"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Generate content_id like content0000001
def generate_content_id(cursor):
    cursor.execute("SELECT content_id FROM aboutus_whychoose ORDER BY content_id DESC LIMIT 1")
    row = cursor.fetchone()
    if row and row["content_id"]:
        last_id = int(row["content_id"].replace("content", ""))
        return f"content{last_id + 1:07d}"
    return "content0000001"

# ---------------------- ADD ----------------------
@router.post("/aboutus_whychoose/")
async def add_whychoose_item(
    heading: Optional[str] = Form(None),
    items: Optional[str] = Form(None),
    button: Optional[str] = Form(None),
    bg_color: Optional[str] = Form(None),
    icon_box: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
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
        sql = """
            INSERT INTO aboutus_whychoose
            (content_id, heading, items, button, bg_color, icon_box, image, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            content_id, heading, items, button, bg_color, icon_box, relative_path, created_by
        )
        cursor.execute(sql, values)
        db.commit()
        return {"message": "Item added", "content_id": content_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ---------------------- FETCH ----------------------
@router.get("/aboutus_whychoose/")
def fetch_all_items():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM aboutus_whychoose ORDER BY content_id DESC")
        return {"data": cursor.fetchall()}
    finally:
        db.close()

# ---------------------- UPDATE ----------------------
@router.put("/aboutus_whychoose/{content_id}")
async def update_whychoose_item(
    content_id: str,
    heading: Optional[str] = Form(None),
    items: Optional[str] = Form(None),
    button: Optional[str] = Form(None),
    bg_color: Optional[str] = Form(None),
    icon_box: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    updated_by: Optional[str] = Form(None)
):
    db, cursor = get_global_tiffin_db_connection()
    cursor.execute("SELECT * FROM aboutus_whychoose WHERE content_id = %s", (content_id,))
    existing = cursor.fetchone()

    if not existing:
        db.close()
        raise HTTPException(status_code=404, detail="Item not found")

    image_path = existing["image"]
    if image and image.filename:
        # Remove old image
        if image_path:
            old_local_path = image_path.replace("/uploads", "uploads")
            if os.path.exists(old_local_path):
                os.remove(old_local_path)

        ext = os.path.splitext(image.filename)[1]
        filename = f"{content_id}{ext}"
        image_path = f"/uploads/about_us_resource/{filename}"
        file_path = os.path.join("uploads/about_us_resource", filename)

        with open(file_path, "wb") as f:
            f.write(await image.read())

    fields, values = [], []

    if heading is not None:
        fields.append("heading = %s")
        values.append(heading)
    if items is not None:
        fields.append("items = %s")
        values.append(items)
    if button is not None:
        fields.append("button = %s")
        values.append(button)
    if bg_color is not None:
        fields.append("bg_color = %s")
        values.append(bg_color)
    if icon_box is not None:
        fields.append("icon_box = %s")
        values.append(icon_box)
    if image and image.filename:
        fields.append("image = %s")
        values.append(image_path)
    if updated_by is not None:
        fields.append("updated_by = %s")
        values.append(updated_by)

    if not fields:
        db.close()
        return {"message": "No update data provided"}

    sql = f"UPDATE aboutus_whychoose SET {', '.join(fields)} WHERE content_id = %s"
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

# ---------------------- DELETE ----------------------
@router.delete("/aboutus_whychoose/{content_id}")
def delete_whychoose_item(content_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT image FROM aboutus_whychoose WHERE content_id = %s", (content_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")

        image_path = row["image"]
        if image_path:
            local_path = image_path.replace("/uploads", "uploads")
            if os.path.exists(local_path):
                os.remove(local_path)

        cursor.execute("DELETE FROM aboutus_whychoose WHERE content_id = %s", (content_id,))
        db.commit()
        return {"message": "Item and associated image deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
