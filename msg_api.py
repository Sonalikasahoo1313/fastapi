from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from db_connection import get_global_tiffin_db_connection

router = APIRouter()

# ------------------ Models ------------------
class Message(BaseModel):
    msg: str
    action: Optional[str] = "unpublished"
    created_by: str

class UpdateMessage(BaseModel):
    msg: Optional[str] = None
    action: Optional[str] = None
    updated_by: str

# ------------------ Auto Generate msg_id ------------------
def generate_msg_id(cursor):
    cursor.execute("SELECT msg_id FROM msg_table ORDER BY msg_id DESC LIMIT 1")
    result = cursor.fetchone()

    if result:
        last_id = result["msg_id"]
        num = int(last_id.replace("msg", ""))
        new_id = f"msg{num + 1:07d}"
    else:
        new_id = "msg0000001"

    return new_id

# ------------------ Add Message ------------------
@router.post("/msg/add")
def add_message(message: Message):
    db, cursor = get_global_tiffin_db_connection()
    try:
        msg_id = generate_msg_id(cursor)

        query = """
            INSERT INTO msg_table (msg_id, msg, action, created_by)
            VALUES (%s, %s, %s, %s)
        """
        values = (msg_id, message.msg, message.action, message.created_by)

        cursor.execute(query, values)
        db.commit()

        return {"message": "Message added successfully", "msg_id": msg_id}
    finally:
        db.close()

# ------------------ Fetch All Messages ------------------
@router.get("/msg/all")
def fetch_all_messages():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM msg_table")
        return cursor.fetchall()
    finally:
        db.close()

# ------------------ Update Message by ID ------------------
@router.put("/msg/update/{msg_id}")
def update_message(msg_id: str, update_data: UpdateMessage):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM msg_table WHERE msg_id = %s", (msg_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Message not found")

        fields = []
        values = []

        if update_data.msg is not None:
            fields.append("msg = %s")
            values.append(update_data.msg)

        if update_data.action is not None:
            fields.append("action = %s")
            values.append(update_data.action)

        # Always update updated_by
        fields.append("updated_by = %s")
        values.append(update_data.updated_by)

        query = f"UPDATE msg_table SET {', '.join(fields)} WHERE msg_id = %s"
        values.append(msg_id)

        cursor.execute(query, tuple(values))
        db.commit()

        return {"message": "Message updated successfully"}
    finally:
        db.close()

# ------------------ Delete Message by ID ------------------
@router.delete("/msg/delete/{msg_id}")
def delete_message(msg_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM msg_table WHERE msg_id = %s", (msg_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Message not found")

        cursor.execute("DELETE FROM msg_table WHERE msg_id = %s", (msg_id,))
        db.commit()

        return {"message": "Message deleted successfully"}
    finally:
        db.close()
