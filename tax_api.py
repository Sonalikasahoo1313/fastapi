from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from db_connection import get_global_tiffin_db_connection

router = APIRouter()

# ------------------ Models ------------------
class Tax(BaseModel):
    name: str
    type: str  # 'tax' or 'charges'
    value: float
    value_type: str  # 'percentage' or 'pound'
    created_by: str

class UpdateTax(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    value: Optional[float] = None
    value_type: Optional[str] = None
    updated_by: str

# ------------------ Generate New Tax ID ------------------
def generate_tax_id(cursor):
    cursor.execute("SELECT tax_id FROM taxes ORDER BY tax_id DESC LIMIT 1")
    last = cursor.fetchone()
    if last:
        last_id = last['tax_id']
        num = int(last_id.replace("tax", ""))
        new_id = f"tax{num + 1:07d}"
    else:
        new_id = "tax0000001"
    return new_id

# ------------------ Add Tax ------------------
@router.post("/taxes/add")
def add_tax(tax: Tax):
    db, cursor = get_global_tiffin_db_connection()
    try:
        tax_id = generate_tax_id(cursor)
        query = """
            INSERT INTO taxes (tax_id, name, type, value, value_type, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (tax_id, tax.name, tax.type, tax.value, tax.value_type, tax.created_by)
        cursor.execute(query, values)
        db.commit()
        return {"message": "Tax added successfully", "tax_id": tax_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ------------------ Get All Taxes ------------------
@router.get("/taxes/all")
def get_all_taxes():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM taxes ORDER BY tax_id DESC")
        return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ------------------ Delete Tax by ID ------------------
@router.delete("/taxes/delete/{tax_id}")
def delete_tax(tax_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM taxes WHERE tax_id = %s", (tax_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Tax not found")

        cursor.execute("DELETE FROM taxes WHERE tax_id = %s", (tax_id,))
        db.commit()
        return {"message": "Tax deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ------------------ Update Tax by ID ------------------
@router.put("/taxes/update/{tax_id}")
def update_tax(tax_id: str, data: UpdateTax):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM taxes WHERE tax_id = %s", (tax_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Tax not found")

        fields = []
        values = []

        if data.name is not None:
            fields.append("name = %s")
            values.append(data.name)
        if data.type is not None:
            fields.append("type = %s")
            values.append(data.type)
        if data.value is not None:
            fields.append("value = %s")
            values.append(data.value)
        if data.value_type is not None:
            fields.append("value_type = %s")
            values.append(data.value_type)

        # Always update updated_by
        fields.append("updated_by = %s")
        values.append(data.updated_by)

        if not fields:
            raise HTTPException(status_code=400, detail="No data to update")

        update_query = f"UPDATE taxes SET {', '.join(fields)} WHERE tax_id = %s"
        values.append(tax_id)
        cursor.execute(update_query, tuple(values))
        db.commit()

        return {"message": "Tax updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
