from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from db_connection import get_global_tiffin_db_connection
import os
import shutil
from uuid import uuid4

router = APIRouter()

# Upload directory
UPLOAD_DIR = "uploads/menu_resource"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Generate unique menu_id like menu0000001
def generate_menu_id(cursor):
    cursor.execute("SELECT menu_id FROM menu ORDER BY menu_id DESC LIMIT 1")
    last = cursor.fetchone()
    if last:
        last_num = int(last["menu_id"].replace("menu", ""))
        new_num = last_num + 1
    else:
        new_num = 1
    return f"menu{str(new_num).zfill(7)}"

# Validate dish against category
def is_valid_dish(cursor, dishname, category):
    cursor.execute(
        "SELECT * FROM dishes WHERE LOWER(TRIM(dishname)) = LOWER(TRIM(%s)) AND category = %s",
        (dishname, category)
    )
    return cursor.fetchone() is not None

# ------------------ Add Menu ------------------
@router.post("/menu/add")
async def add_menu(
    week: str = Form(...),
    day: str = Form(...),
    menu_name: str = Form(...),
    veg: str = Form(None),
    nonveg: str = Form(None),
    vegan: str = Form(None),
    extra: str = Form(None),
    price: float = Form(...),
    created_by: str = Form(...),
    image: UploadFile = File(None)
):
    db, cursor = get_global_tiffin_db_connection()
    try:
        menu_id = generate_menu_id(cursor)

        image_url = None
        if image and image.filename:
            ext = image.filename.split('.')[-1]
            suffix = uuid4().hex[:8]
            filename = f"{menu_id}_{suffix}.{ext}"
            save_path = os.path.join(UPLOAD_DIR, filename)
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_url = f"/uploads/menu_resource/{filename}"

        # Validation
        if veg and not is_valid_dish(cursor, veg, "veg"):
            raise HTTPException(status_code=400, detail=f"{veg} is not a valid veg dish.")
        if nonveg and not is_valid_dish(cursor, nonveg, "nonveg"):
            raise HTTPException(status_code=400, detail=f"{nonveg} is not a valid nonveg dish.")
        if vegan and not is_valid_dish(cursor, vegan, "vegan"):
            raise HTTPException(status_code=400, detail=f"{vegan} is not a valid vegan dish.")
        if extra:
            extra_dishes = [d.strip() for d in extra.split(",") if d.strip()]
            for dish in extra_dishes:
                if not is_valid_dish(cursor, dish, "extra"):
                    raise HTTPException(status_code=400, detail=f"{dish} is not a valid extra dish.")
            extra = ", ".join(extra_dishes)

        sql = """
            INSERT INTO menu (
                menu_id, week, day, menu_name, veg, nonveg, vegan, extra, image, price, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (menu_id, week, day, menu_name, veg, nonveg, vegan, extra, image_url, price, created_by)
        cursor.execute(sql, values)
        db.commit()

        return {"message": "Menu added successfully", "menu_id": menu_id, "image_url": image_url}
    finally:
        db.close()

# ------------------ Fetch All Menus ------------------
 

@router.get("/menu/fetch_all")
def fetch_all_menu():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM menu")
        return {"data": cursor.fetchall()}
    finally:
        db.close()
# ------------------ Fetch Menu By ID ------------------
@router.get("/menu/{menu_id}")
def fetch_menu_by_id(menu_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM menu WHERE menu_id = %s", (menu_id,))
        menu = cursor.fetchone()
        if not menu:
            raise HTTPException(status_code=404, detail="Menu not found")
        return {"data": menu}
    finally:
        db.close()
# ------------------ Update Menu ------------------
@router.put("/menu/update/{menu_id}")
async def update_menu(
    menu_id: str,
    week: str = Form(...),
    day: str = Form(...),
    menu_name: str = Form(...),
    veg: str = Form(None),
    nonveg: str = Form(None),
    vegan: str = Form(None),
    extra: str = Form(None),
    price: float = Form(...),
    updated_by: str = Form(...),
    image: UploadFile = File(None)
):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM menu WHERE menu_id = %s", (menu_id,))
        menu = cursor.fetchone()
        if not menu:
            raise HTTPException(status_code=404, detail="Menu not found")

        image_url = menu["image"]
        if image and image.filename:
            ext = image.filename.split('.')[-1]
            suffix = uuid4().hex[:8]
            filename = f"{menu_id}_{suffix}.{ext}"
            save_path = os.path.join(UPLOAD_DIR, filename)
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_url = f"/uploads/menu_resource/{filename}"

            # delete old image
            if menu["image"]:
                old_path = os.path.join("uploads", menu["image"].replace("/uploads/", ""))
                if os.path.exists(old_path):
                    os.remove(old_path)

        # Validation
        if veg and not is_valid_dish(cursor, veg, "veg"):
            raise HTTPException(status_code=400, detail=f"{veg} is not a valid veg dish.")
        if nonveg and not is_valid_dish(cursor, nonveg, "nonveg"):
            raise HTTPException(status_code=400, detail=f"{nonveg} is not a valid nonveg dish.")
        if vegan and not is_valid_dish(cursor, vegan, "vegan"):
            raise HTTPException(status_code=400, detail=f"{vegan} is not a valid vegan dish.")
        if extra:
            extra_dishes = [d.strip() for d in extra.split(",") if d.strip()]
            for dish in extra_dishes:
                if not is_valid_dish(cursor, dish, "extra"):
                    raise HTTPException(status_code=400, detail=f"{dish} is not a valid extra dish.")
            extra = ", ".join(extra_dishes)

        sql = """
            UPDATE menu
            SET week=%s, day=%s, menu_name=%s, veg=%s, nonveg=%s, vegan=%s,
                extra=%s, image=%s, price=%s, updated_by=%s
            WHERE menu_id=%s
        """
        values = (week, day, menu_name, veg, nonveg, vegan, extra, image_url, price, updated_by, menu_id)
        cursor.execute(sql, values)
        db.commit()

        return {"message": "Menu updated successfully", "menu_id": menu_id, "image_url": image_url}
    finally:
        db.close()

# ------------------ Delete Menu ------------------
@router.delete("/menu/delete/{menu_id}")
def delete_menu(menu_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM menu WHERE menu_id = %s", (menu_id,))
        menu = cursor.fetchone()
        if not menu:
            raise HTTPException(status_code=404, detail="Menu not found")

        image_url = menu["image"]
        if image_url:
            file_path = os.path.join("uploads", image_url.replace("/uploads/", ""))
            if os.path.exists(file_path):
                os.remove(file_path)

        cursor.execute("DELETE FROM menu WHERE menu_id = %s", (menu_id,))
        db.commit()

        return {"message": f"Menu {menu_id} deleted successfully and associated image removed."}
    finally:
        db.close()
