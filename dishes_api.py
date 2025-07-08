from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from db_connection import get_global_tiffin_db_connection
import os
import shutil
from uuid import uuid4

router = APIRouter()

UPLOAD_DIR = "uploads/dishes_resource"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------- ID Generator ----------------------
def generate_dish_id(cursor):
    cursor.execute("SELECT dish_id FROM dishes ORDER BY dish_id DESC LIMIT 1")
    last = cursor.fetchone()
    if last:
        last_num = int(last["dish_id"].replace("dish", ""))
        new_num = last_num + 1
    else:
        new_num = 1
    return f"dish{str(new_num).zfill(7)}"

# ---------------------- Add Dish ----------------------
@router.post("/dishes/add")
async def add_dish(
    dishname: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    created_by: str = Form(...),
    photo: UploadFile = File(None)
):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM dishes WHERE dishname = %s", (dishname,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Dish name already exists")

        dish_id = generate_dish_id(cursor)
        media_path = None

        if photo and photo.filename.strip() != "":
            ext = photo.filename.split('.')[-1]
            suffix = uuid4().hex[:8]
            filename = f"{dish_id}_{suffix}.{ext}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            media_path = f"/uploads/dishes_resource/{filename}"  # relative path

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)

        sql = """
            INSERT INTO dishes (
                dish_id, dishname, category, price, photo, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (dish_id, dishname, category, price, media_path, created_by))
        db.commit()

        return {"message": "Dish added successfully", "dish_id": dish_id}
    finally:
        db.close()

# ---------------------- Fetch All Dishes ----------------------
@router.get("/dishes/fetch_all")
def fetch_all_dishes():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM dishes ORDER BY created_on DESC")
        dishes = cursor.fetchall()
        return {"data": dishes}
    finally:
        db.close()

# ---------------------- Update Dish ----------------------
@router.put("/dishes/update/{dish_id}")
async def update_dish(
    dish_id: str,
    dishname: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    updated_by: str = Form(...),
    photo: UploadFile = File(None)
):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM dishes WHERE dish_id = %s", (dish_id,))
        dish = cursor.fetchone()
        if not dish:
            raise HTTPException(status_code=404, detail="Dish not found")

        cursor.execute("SELECT * FROM dishes WHERE dishname = %s AND dish_id != %s", (dishname, dish_id))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Another dish with the same name exists")

        media_path = dish["photo"]

        if photo and photo.filename.strip() != "":
            ext = photo.filename.split('.')[-1]
            suffix = uuid4().hex[:8]
            filename = f"{dish_id}_{suffix}.{ext}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            media_path = f"/uploads/dishes_resource/{filename}"

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)

            # Remove old image
            old_path = dish["photo"]
            if old_path:
                local_path = old_path.replace("/uploads", "uploads")
                if os.path.exists(local_path):
                    os.remove(local_path)

        sql = """
            UPDATE dishes
            SET dishname = %s, category = %s, price = %s,
                photo = %s, updated_by = %s
            WHERE dish_id = %s
        """
        values = (dishname, category, price, media_path, updated_by, dish_id)
        cursor.execute(sql, values)
        db.commit()

        return {"message": "Dish updated successfully", "dish_id": dish_id}
    finally:
        db.close()


 # ---------------------- Fetch Dish By ID ----------------------
@router.get("/dishes/{dish_id}")
def fetch_dish_by_id(dish_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM dishes WHERE dish_id = %s", (dish_id,))
        dish = cursor.fetchone()
        if not dish:
            raise HTTPException(status_code=404, detail="Dish not found")
        return {"data": dish}
    finally:
        db.close()
# ---------------------- Delete Dish ----------------------
@router.delete("/dishes/delete/{dish_id}")
def delete_dish(dish_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM dishes WHERE dish_id = %s", (dish_id,))
        dish = cursor.fetchone()
        if not dish:
            raise HTTPException(status_code=404, detail="Dish not found")

        photo_path = dish.get("photo")
        if photo_path:
            local_path = photo_path.replace("/uploads", "uploads")
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to delete image file: {e}")

        cursor.execute("DELETE FROM dishes WHERE dish_id = %s", (dish_id,))
        db.commit()

        return {"message": f"Dish {dish_id} deleted successfully, and image file removed."}
    finally:
        db.close()
