from fastapi import APIRouter, HTTPException, Form
from datetime import datetime
import mysql.connector
import re
from db_connection import get_global_tiffin_db_connection

router = APIRouter()

# ----------------- Helper to Generate subscriber_id -----------------
def generate_subscriber_id(cursor):
    cursor.execute("SELECT subscriber_id FROM subscriber ORDER BY subscriber_id DESC LIMIT 1")
    result = cursor.fetchone()
    if result and result["subscriber_id"]:
        last_id = int(re.search(r'\d+', result["subscriber_id"]).group())
        new_id = f"scb{last_id + 1:07d}"
    else:
        new_id = "scb0000001"
    return new_id

# ----------------- Add Subscriber -----------------
@router.post("/subscriber/add")
def add_subscriber(
    name: str = Form(...),
    email: str = Form(...),
    created_by: str = Form(...)
):
    db, cursor = get_global_tiffin_db_connection()
    try:
        subscriber_id = generate_subscriber_id(cursor)
        status = 'subscribe'

        query = """
            INSERT INTO subscriber (subscriber_id, name, email, status, created_by)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (subscriber_id, name, email, status, created_by)
        cursor.execute(query, values)
        db.commit()

        return {"message": "Subscriber added successfully", "subscriber_id": subscriber_id}

    except mysql.connector.IntegrityError as err:
        db.rollback()
        if "1062" in str(err):
            raise HTTPException(status_code=400, detail="Email already subscribed")
        raise HTTPException(status_code=500, detail=f"Database Error: {err}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ----------------- Fetch All Subscribers -----------------
@router.get("/subscriber/all")
def fetch_all_subscribers():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM subscriber ORDER BY created_on DESC")
        subscribers = cursor.fetchall()
        return subscribers
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database Error: {err}")
    finally:
        db.close()

# ----------------- Update Subscriber -----------------
@router.put("/subscriber/update/{subscriber_id}")
def update_subscriber(
    subscriber_id: str,
    name: str = Form(...),
    email: str = Form(...),
    status: str = Form(...),
    updated_by: str = Form(...)
):
    db, cursor = get_global_tiffin_db_connection()
    try:
        query = """
            UPDATE subscriber 
            SET name=%s, email=%s, status=%s, updated_by=%s 
            WHERE subscriber_id=%s
        """
        values = (name, email, status, updated_by, subscriber_id)
        cursor.execute(query, values)
        db.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        return {"message": "Subscriber updated successfully"}

    except mysql.connector.IntegrityError as err:
        db.rollback()
        if "1062" in str(err):
            raise HTTPException(status_code=400, detail="Email already in use")
        raise HTTPException(status_code=500, detail=f"Database Error: {err}")
    finally:
        db.close()

# ----------------- Delete Subscriber -----------------
@router.delete("/subscriber/delete/{subscriber_id}")
def delete_subscriber(subscriber_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("DELETE FROM subscriber WHERE subscriber_id = %s", (subscriber_id,))
        db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        return {"message": "Subscriber deleted successfully"}

    except mysql.connector.Error as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {err}")
    finally:
        db.close()
