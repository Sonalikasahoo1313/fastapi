from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import bcrypt
from db_connection import get_global_tiffin_db_connection, get_vault_db_connection
from datetime import datetime

router = APIRouter()

# ------------------ Models ------------------
class Customer(BaseModel):
    name: str
    email: str
    phone_number: str
    password: str
    address: Optional[str] = None
    status: Optional[str] = "active"
    created_by: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateCustomer(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    updated_by: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    updated_by: str

# ------------------ Password Utilities ------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# ------------------ Customer ID Generator ------------------
def generate_customer_id(cursor):
    cursor.execute("SELECT customer_id FROM customer ORDER BY customer_id DESC LIMIT 1")
    result = cursor.fetchone()

    if result:
        last_id = result[0] if isinstance(result, tuple) else result['customer_id']
        num_part = int(last_id.replace("Cmr", ""))
        return f"Cmr{num_part + 1:07d}"
    return "Cmr0000001"

# ------------------ Register Customer ------------------
@router.post("/customer/register")
def register_customer(customer: Customer):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM customer WHERE email = %s", (customer.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        customer_id = generate_customer_id(cursor)
        hashed_pwd = hash_password(customer.password)

        query = """
            INSERT INTO customer (
                customer_id, name, email, phone_number, password, address, status,
                created_by, total_order
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            customer_id, customer.name, customer.email, customer.phone_number, hashed_pwd,
            customer.address, customer.status, customer.created_by, 0
        )
        cursor.execute(query, values)
        db.commit()
        return {"message": "Customer registered successfully", "customer_id": customer_id}
    finally:
        db.close()

# ------------------ Login Customer ------------------
@router.post("/customer/login")
def login_customer(login_data: LoginRequest):
    vault_db, vault_cursor = get_vault_db_connection()
    db, cursor = get_global_tiffin_db_connection()
    try:
        vault_cursor.execute("SELECT status FROM vault_users WHERE email = %s", (login_data.email,))
        vault_user = vault_cursor.fetchone()

        if not vault_user or vault_user["status"].lower() != "active":
            raise HTTPException(status_code=403, detail="Access denied. Please contact the administrator.")

        cursor.execute("SELECT * FROM customer WHERE email = %s", (login_data.email,))
        customer = cursor.fetchone()

        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        if customer["status"].lower() != "active":
            raise HTTPException(status_code=403, detail="Your account is inactive")

        if not verify_password(login_data.password, customer["password"]):
            raise HTTPException(status_code=401, detail="Incorrect password")

        return {
            "message": "Login successful",
            "customer": {
                "customer_id": customer["customer_id"],
                "name": customer["name"],
                "email": customer["email"],
                "phone_number": customer["phone_number"],
                "address": customer["address"],
                "created_on": customer["created_on"],
                "status": customer["status"],
                "total_order": customer["total_order"],
                "created_by": customer["created_by"],
                "updated_on": customer["updated_on"],
                "updated_by": customer["updated_by"]
            }
        }
    finally:
        db.close()
        vault_db.close()

# ------------------ Get All Customers ------------------
@router.get("/customer/all")
def get_all_customers():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM customer")
        return cursor.fetchall()
    finally:
        db.close()

# ------------------ Get Customer by ID ------------------
@router.get("/customer/{customer_id}")
def get_customer_by_id(customer_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM customer WHERE customer_id = %s", (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer
    finally:
        db.close()

# ------------------ Update Customer ------------------
@router.put("/customer/update/{customer_id}")
def update_customer(customer_id: str, updated_data: UpdateCustomer):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM customer WHERE customer_id = %s", (customer_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Customer not found")

        fields = []
        values = []

        if updated_data.name:
            fields.append("name = %s")
            values.append(updated_data.name)
        if updated_data.email:
            fields.append("email = %s")
            values.append(updated_data.email)
        if updated_data.phone_number:
            fields.append("phone_number = %s")
            values.append(updated_data.phone_number)
        if updated_data.password:
            fields.append("password = %s")
            values.append(hash_password(updated_data.password))
        if updated_data.address:
            fields.append("address = %s")
            values.append(updated_data.address)
        if updated_data.status:
            fields.append("status = %s")
            values.append(updated_data.status)

        fields.append("updated_on = %s")
        values.append(datetime.now())
        fields.append("updated_by = %s")
        values.append(updated_data.updated_by)

        update_query = f"UPDATE customer SET {', '.join(fields)} WHERE customer_id = %s"
        values.append(customer_id)

        cursor.execute(update_query, tuple(values))
        db.commit()
        return {"message": "Customer updated successfully"}
    finally:
        db.close()

# ------------------ Change Password ------------------
@router.put("/customer/change-password/{customer_id}")
def change_password(customer_id: str, data: ChangePasswordRequest):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT password FROM customer WHERE customer_id = %s", (customer_id,))
        customer = cursor.fetchone()

        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        if not verify_password(data.old_password, customer["password"]):
            raise HTTPException(status_code=401, detail="Old password is incorrect")

        new_hashed = hash_password(data.new_password)

        cursor.execute(
            "UPDATE customer SET password = %s, updated_on = %s, updated_by = %s WHERE customer_id = %s",
            (new_hashed, datetime.now(), data.updated_by, customer_id)
        )
        db.commit()
        return {"message": "Password changed successfully"}
    finally:
        db.close()

# ------------------ Delete Customer ------------------
@router.delete("/customer/delete/{customer_id}")
def delete_customer(customer_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("DELETE FROM customer WHERE customer_id = %s", (customer_id,))
        db.commit()
        return {"message": "Customer deleted successfully"}
    finally:
        db.close()
