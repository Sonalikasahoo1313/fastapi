from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from db_connection import get_global_tiffin_db_connection

router = APIRouter()

# ------------------ ID Generator ------------------
def generate_promo_id(cursor):
    cursor.execute("SELECT promo_id FROM promotion ORDER BY promo_id DESC LIMIT 1")
    last = cursor.fetchone()
    if last and last["promo_id"]:
        last_num = int(last["promo_id"][5:])  # Remove 'promo'
        new_num = last_num + 1
    else:
        new_num = 1
    return f"promo{new_num:07d}"

# ------------------ Models ------------------
class Promotion(BaseModel):
    pcode: str
    discount: float
    description: Optional[str] = None
    status: str
    created_by: Optional[str] = None

class UpdatePromotion(BaseModel):
    pcode: Optional[str] = None
    discount: Optional[float] = None
    description: Optional[str] = None
    status: Optional[str] = None
    updated_by: Optional[str] = None

# ------------------ Add Promotion ------------------
@router.post("/promotion/add")
def add_promotion(promotion: Promotion):
    db, cursor = get_global_tiffin_db_connection()
    try:
        promo_id = generate_promo_id(cursor)

        query = """
            INSERT INTO promotion (promo_id, pcode, discount, description, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            promo_id,
            promotion.pcode,
            promotion.discount,
            promotion.description,
            promotion.status,
            promotion.created_by,
        )
        cursor.execute(query, values)
        db.commit()

        return {
            "message": "Promotion added successfully",
            "promo_id": promo_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ------------------ Get All Promotions ------------------
@router.get("/promotion/all")
def get_all_promotions():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM promotion ORDER BY promo_id DESC")
        data = cursor.fetchall()
        return {"promotions": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ------------------ Update Promotion ------------------
@router.put("/promotion/update/{promo_id}")
def update_promotion(promo_id: str, promotion: UpdatePromotion):
    db, cursor = get_global_tiffin_db_connection()
    try:
        fields = []
        values = []

        for key, value in promotion.dict(exclude_unset=True).items():
            fields.append(f"{key} = %s")
            values.append(value)

        if not fields:
            raise HTTPException(status_code=400, detail="No data provided for update")

        values.append(promo_id)

        query = f"""
            UPDATE promotion SET {', '.join(fields)} WHERE promo_id = %s
        """
        cursor.execute(query, tuple(values))
        db.commit()

        return {"message": "Promotion updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ------------------ Delete Promotion ------------------
@router.delete("/promotion/delete/{promo_id}")
def delete_promotion(promo_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("DELETE FROM promotion WHERE promo_id = %s", (promo_id,))
        db.commit()

        return {"message": f"Promotion '{promo_id}' deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
