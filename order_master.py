from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
import pytz
import mysql.connector
from db_connection import get_global_tiffin_db_connection  # updated import

router = APIRouter()

# ==================== Pydantic Models ====================

class ExtraDish(BaseModel):
    dish_id: str
    quantity: int

class OrderItem(BaseModel):
    menu_id: str
    meal_type: str
    note: Optional[str] = None  # ✅ NEW FIELD
    extra_dishes: Optional[List[ExtraDish]] = None


class OrderBase(BaseModel):
    customer_id: str
    delivery_address: Optional[str] = None
    delivery_note: Optional[str] = None  # ✅ NEW FIELD
    payment_mode: Optional[str] = None
    total_amount: float
    status: Optional[str] = "pending"
    created_by: str
    review: Optional[str] = None
    review_status: Optional[str] = None
    cancel_status: Optional[str] = None
    cancel_reason: Optional[str] = None
    order_items: List[OrderItem]



class OrderUpdate(BaseModel):
    delivery_address: Optional[str] = None
    delivery_note: Optional[str] = None  # ✅ NEW FIELD
    payment_mode: Optional[str] = None
    total_amount: Optional[float] = None
    status: Optional[str] = None
    review: Optional[str] = None
    review_status: Optional[str] = None
    cancel_status: Optional[str] = None
    cancel_reason: Optional[str] = None
    updated_by: str

 
    
class OrderItemDetails(BaseModel):
    item_id: str
    meal_type: str
    note: Optional[str] = None  # ✅ NEW FIELD


class OrderUpdateDetails(BaseModel):
    delivery_address: Optional[str] = None
    payment_mode: Optional[str] = None
    total_amount: Optional[float] = None
    delivery_note: Optional[str] = None  # ✅ ADD THIS LINE
    updated_by: str
    order_items: Optional[List[OrderItemDetails]] = None

    
class OrdItemUpdate(BaseModel):
    meal_type: Optional[str] = None
    note: Optional[str] = None
    status: Optional[str] = None
    cancelreason: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None



# ==================== Helper Functions ====================

def uk_now() -> datetime:
    tz = pytz.timezone('Europe/London')
    return datetime.now(tz)

def format_uk(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def generate_order_id():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT order_id FROM order_master ORDER BY order_id DESC LIMIT 1")
        last = cursor.fetchone()
        num = int(last["order_id"].replace("ORD", "")) + 1 if last else 1
        return f"ORD{num:07d}"
    finally:
        cursor.close()
        db.close()

def generate_item_id():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT item_id FROM orditem_details ORDER BY item_id DESC LIMIT 1")
        last = cursor.fetchone()
        num = int(last["item_id"].replace("item", "")) + 1 if last else 1
        return f"item{num:07d}"
    finally:
        cursor.close()
        db.close()

def generate_ordextra_id():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT ordextra_id FROM ordextra_details ORDER BY ordextra_id DESC LIMIT 1")
        last = cursor.fetchone()
        num = int(last["ordextra_id"].replace("extra", "")) + 1 if last else 1
        return f"extra{num:07d}"
    finally:
        cursor.close()
        db.close()
        
        
def get_delivery_info(menu_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT week, day FROM menu WHERE menu_id=%s", (menu_id,))
        menu_row = cursor.fetchone()
        if not menu_row:
            raise HTTPException(status_code=400, detail=f"No menu found for menu_id={menu_id}")

        week_str = menu_row["week"]  # e.g., "week1"
        day_str = menu_row["day"]    # e.g., "day2"
        week_num = int(week_str.replace("week", ""))
        day_num = int(day_str.replace("day", ""))

        base_date = date(2025, 6, 30)
        days_to_add = (week_num - 1) * 7 + (day_num - 1)
        target_date = base_date + timedelta(days=days_to_add)

        today = date.today()

        while target_date < today:
            year = base_date.year + ((base_date.month + 1) // 13)
            month = (base_date.month + 1) % 12 or 12
            base_date = date(year, month, 30)
            target_date = base_date + timedelta(days=days_to_add)

        return target_date, week_str, day_str

    finally:
        cursor.close()
        db.close()


# ==================== Endpoints ====================

@router.post("/orders/add")
def add_order(order: OrderBase):
    db, cursor = get_global_tiffin_db_connection()
    try:
        order_id = generate_order_id()
        order_date = uk_now()

        # Insert into order_master
        cursor.execute(
            """
            INSERT INTO order_master (
                order_id, customer_id, order_date, delivery_address,
                delivery_note, payment_mode, total_amount, status, created_by,
                review, review_status, cancel_status, cancel_reason
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                order_id, order.customer_id, order_date, order.delivery_address,
                order.delivery_note, order.payment_mode, order.total_amount, order.status,
                order.created_by, order.review, order.review_status,
                order.cancel_status, order.cancel_reason
            )
        )
        db.commit()

        created_items = []  # ✅ Collect item_ids

        # ✅ Fetch last ordextra_id once and initialize counter
        cursor.execute("SELECT ordextra_id FROM ordextra_details ORDER BY ordextra_id DESC LIMIT 1")
        last_extra = cursor.fetchone()
        start_num = int(last_extra["ordextra_id"].replace("extra", "")) + 1 if last_extra else 1
        extra_counter = start_num

        # Loop over each menu item
        for item in order.order_items:
            # Get target_date, week_str like "week1" and day_str like "day2"
            delivery_date, week_str, day_str = get_delivery_info(item.menu_id)

            item_id = generate_item_id()
            created_items.append(item_id)  # ✅ Add to response list

            cursor.execute(
                """
                INSERT INTO orditem_details (
                    item_id, order_id, menu_id, meal_type, quantity,
                    price, delivery_date, week_number, day_of_week, status, note
                ) VALUES (%s, %s, %s, %s, 1, NULL, %s, %s, %s, 'pending', %s)
                """,
                (
                    item_id, order_id, item.menu_id, item.meal_type,
                    delivery_date, week_str, day_str, item.note
                )
            )

            # ✅ Handle extra dishes with local ID generation
            if item.extra_dishes:
                for extra in item.extra_dishes:
                    ordextra_id = f"extra{extra_counter:07d}"
                    extra_counter += 1  # ✅ Increment locally
                    cursor.execute(
                        """
                        INSERT INTO ordextra_details (ordextra_id, item_id, dish_id, quantity)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (ordextra_id, item_id, extra.dish_id, extra.quantity)
                    )

        db.commit()

        # ✅ Update customer's total_orders field
        update_customer_total_orders(order.customer_id)

        return {
            "message": "Order placed successfully",
            "order_id": order_id,
            "item_ids": created_items  # ✅ Return list of created item_ids
        }

    except mysql.connector.Error as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        db.close()


@router.get("/orders/all")
def fetch_all_orders():
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM order_master ORDER BY order_date DESC")
        orders = cursor.fetchall()

        all_data = []

        for order in orders:
            order_id = order["order_id"]
            order["order_date"] = format_uk(order.get("order_date"))
            order["updated_at"] = format_uk(order.get("updated_at"))

            # Fetch items related to this order
            cursor.execute("SELECT * FROM orditem_details WHERE order_id=%s", (order_id,))
            item_rows = cursor.fetchall()

            item_details = []
            for item in item_rows:
                item_id = item["item_id"]

                # Format delivery date
                item["delivery_date"] = format_uk(item.get("delivery_date"))

                # Fetch extras for this item
                cursor.execute("SELECT * FROM ordextra_details WHERE item_id=%s", (item_id,))
                extras = cursor.fetchall()

                # Combine item and its extras
                item_details.append({
                    "item": item,
                    "extra_dishes": extras
                })

            all_data.append({
                "order": order,
                "order_items": item_details
            })

        return all_data

    finally:
        cursor.close()
        db.close()


@router.get("/orders/{order_id}")
def fetch_order(order_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute(
            "SELECT * FROM order_master WHERE order_id=%s",
            (order_id,)
        )
        order = cursor.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order["order_date"] = format_uk(order.get("order_date"))
        order["updated_at"] = format_uk(order.get("updated_at"))

        cursor.execute(
            "SELECT * FROM orditem_details WHERE order_id=%s",
            (order_id,)
        )
        order_items = cursor.fetchall()

        extra_items = []
        for oi in order_items:
            cursor.execute(
                "SELECT * FROM ordextra_details WHERE item_id=%s",
                (oi["item_id"],)
            )
            extra_items.extend(cursor.fetchall())

        return {"order": order, "items": order_items, "extra_dishes": extra_items}
    finally:
        cursor.close()
        db.close()
        
        
@router.put("/orders/update/{order_id}")
def update_order(order_id: str, data: OrderUpdate):
    db, cursor = get_global_tiffin_db_connection()
    try:
        # Check if the order exists
        cursor.execute(
            "SELECT customer_id FROM order_master WHERE order_id=%s",
            (order_id,)
        )
        old_order = cursor.fetchone()
        if not old_order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Prepare update fields and values
        updates = []
        vals = []
        update_data = data.dict(exclude_unset=True, exclude={"updated_by"})

        # Validate if cancel reason is required
        if update_data.get("status") == "cancel" and not update_data.get("cancel_reason"):
            raise HTTPException(
                status_code=400,
                detail="cancel_reason is required when status is 'cancel'"
            )

        # Append all updatable fields
        for k, v in update_data.items():
            updates.append(f"{k}=%s")
            vals.append(v)

        # Append timestamps and updated_by
        updates.append("updated_at=%s")
        vals.append(uk_now())
        updates.append("updated_by=%s")
        vals.append(data.updated_by)

        # Append the WHERE clause value
        vals.append(order_id)

        # Execute the final update
        query = f"UPDATE order_master SET {', '.join(updates)} WHERE order_id=%s"
        cursor.execute(query, tuple(vals))
        db.commit()
        
        # ✅ Update total_orders for this customer if status changed
        update_customer_total_orders(old_order["customer_id"])


        return {"message": "Order updated successfully"}
        
    except mysql.connector.Error as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        db.close()



@router.put("/orders/update_details/{order_id}")
def update_order_details(order_id: str, data: OrderUpdateDetails):
    db, cursor = get_global_tiffin_db_connection()
    try:
        # Check if order exists
        cursor.execute(
            "SELECT customer_id FROM order_master WHERE order_id=%s",
            (order_id,)
        )
        old_order = cursor.fetchone()
        if not old_order:
            raise HTTPException(status_code=404, detail="Order not found")

        # ---------------- Update order_master ----------------
        updates = []
        vals = []
        if data.delivery_address is not None:
            updates.append("delivery_address=%s")
            vals.append(data.delivery_address)
        if data.payment_mode is not None:
            updates.append("payment_mode=%s")
            vals.append(data.payment_mode)
        if data.total_amount is not None:
            updates.append("total_amount=%s")
            vals.append(data.total_amount)
        if data.delivery_note is not None:  # ✅ NEW
            updates.append("delivery_note=%s")
            vals.append(data.delivery_note)

        updates.append("updated_at=%s")
        vals.append(uk_now())
        updates.append("updated_by=%s")
        vals.append(data.updated_by)
        vals.append(order_id)

        if updates:
            query = f"UPDATE order_master SET {', '.join(updates)} WHERE order_id=%s"
            cursor.execute(query, tuple(vals))

        # ---------------- Update order_items ----------------
        if data.order_items:
            for item in data.order_items:
                item_updates = []
                item_vals = []

                if item.meal_type is not None:
                    item_updates.append("meal_type=%s")
                    item_vals.append(item.meal_type)
                if item.note is not None:  # ✅ NEW
                    item_updates.append("note=%s")
                    item_vals.append(item.note)

                if item_updates:
                    item_vals.extend([order_id, item.item_id])
                    query = f"""
                        UPDATE orditem_details
                        SET {', '.join(item_updates)}
                        WHERE order_id=%s AND item_id=%s
                    """
                    cursor.execute(query, tuple(item_vals))

        db.commit()
        return {"message": "Order details updated successfully"}

    except mysql.connector.Error as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(err))

    finally:
        cursor.close()
        db.close()



@router.delete("/orders/delete/{order_id}")
def delete_order(order_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        # Check if the order exists
        cursor.execute(
            "SELECT customer_id FROM order_master WHERE order_id=%s",
            (order_id,)
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Order not found")

        # Step 1: Get item_ids for this order
        cursor.execute("SELECT item_id FROM orditem_details WHERE order_id=%s", (order_id,))
        items = cursor.fetchall()
        item_ids = [item["item_id"] for item in items]

        # Step 2: Delete from ordextra_details
        if item_ids:
            format_strings = ','.join(['%s'] * len(item_ids))
            cursor.execute(f"DELETE FROM ordextra_details WHERE item_id IN ({format_strings})", tuple(item_ids))

        # Step 3: Delete from orditem_details
        cursor.execute("DELETE FROM orditem_details WHERE order_id=%s", (order_id,))

        # Step 4: Delete from order_master
        cursor.execute("DELETE FROM order_master WHERE order_id=%s", (order_id,))
        
        update_customer_total_orders(result["customer_id"])


        db.commit()
        return {"message": "Order and related items deleted successfully"}
        
    except mysql.connector.Error as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        db.close()


@router.get("/orders/customer/{customer_id}")
def fetch_orders_by_customer(customer_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute("SELECT * FROM order_master WHERE customer_id=%s ORDER BY order_date DESC", (customer_id,))
        orders = cursor.fetchall()
        if not orders:
            raise HTTPException(status_code=404, detail="No orders found for this customer")

        result = []

        for order in orders:
            order_id = order["order_id"]
            order["order_date"] = format_uk(order.get("order_date"))
            order["updated_at"] = format_uk(order.get("updated_at"))

            # ✅ Include delivery_note in the response if needed on frontend (already part of `order` dict)

            # Get items for the order
            cursor.execute("SELECT * FROM orditem_details WHERE order_id=%s", (order_id,))
            item_rows = cursor.fetchall()
            items_with_extras = []

            for item in item_rows:
                cursor.execute("SELECT * FROM ordextra_details WHERE item_id=%s", (item["item_id"],))
                extras = cursor.fetchall()
                items_with_extras.append({
                    "menu_id": item["menu_id"],
                    "meal_type": item["meal_type"],
                    "delivery_date": format_uk(item.get("delivery_date")),
                    "week_number": item["week_number"],
                    "day_of_week": item["day_of_week"],
                    "status": item["status"],
                    "note": item.get("note"),  # ✅ Include `note` field
                    "extra_dishes": extras
                })

            result.append({
                "order": order,  # includes delivery_note already
                "order_items": items_with_extras
            })

        return result
    finally:
        cursor.close()
        db.close()


@router.put("/orditem/update/{item_id}")
def update_orditem(item_id: str, data: OrdItemUpdate):
    db, cursor = get_global_tiffin_db_connection()
    try:
        # Fetch existing orditem
        cursor.execute("SELECT order_id FROM orditem_details WHERE item_id=%s", (item_id,))
        existing_item = cursor.fetchone()
        if not existing_item:
            raise HTTPException(status_code=404, detail="Order item not found")

        order_id = existing_item["order_id"]

        updates = []
        vals = []

        # Build dynamic update based on provided fields
        if data.meal_type is not None:
            updates.append("meal_type=%s")
            vals.append(data.meal_type)
        if data.note is not None:
            updates.append("note=%s")
            vals.append(data.note)
        if data.status is not None:
            updates.append("status=%s")
            vals.append(data.status)
            if data.status.lower() == "cancel" and not data.cancelreason:
                raise HTTPException(
                    status_code=400,
                    detail="cancelreason is required if status is 'cancel'"
                )
        if data.cancelreason is not None:
            updates.append("cancelreason=%s")
            vals.append(data.cancelreason)
        if data.quantity is not None:
            updates.append("quantity=%s")
            vals.append(data.quantity)
        if data.price is not None:
            updates.append("price=%s")
            vals.append(data.price)

        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields provided for update")

        # Final update
        vals.append(item_id)
        query = f"UPDATE orditem_details SET {', '.join(updates)} WHERE item_id=%s"
        cursor.execute(query, tuple(vals))
        db.commit()

        # Check if all items for this order are now 'delivered'
        cursor.execute("SELECT status FROM orditem_details WHERE order_id=%s", (order_id,))
        statuses = [row["status"].lower() for row in cursor.fetchall()]
        if statuses and all(status == "delivered" for status in statuses):
            cursor.execute(
                "UPDATE order_master SET status='completed', updated_at=%s WHERE order_id=%s",
                (uk_now(), order_id)
            )
            db.commit()

        return { "message": "Order item updated successfully",
    "order_id": order_id }

    except mysql.connector.Error as err:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(err))

    finally:
        cursor.close()
        db.close()



def update_customer_total_orders(customer_id: str):
    db, cursor = get_global_tiffin_db_connection()
    try:
        cursor.execute(
            "SELECT COUNT(*) AS total FROM order_master WHERE customer_id = %s AND status != 'cancel'",
            (customer_id,)
        )
        total_orders = cursor.fetchone()["total"]
        cursor.execute(
            "UPDATE customer SET total_order = %s WHERE customer_id = %s",
            (total_orders, customer_id)
        )
        db.commit()
    finally:
        cursor.close()
        db.close()
