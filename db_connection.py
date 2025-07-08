import mysql.connector

# ------------------ Global Tiffin DB Connection ------------------
def get_global_tiffin_db_connection():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="global_tiffin_db"
    )
    cursor = db.cursor(dictionary=True)
    return db, cursor

# ------------------ Vault DB Connection ------------------
def get_vault_db_connection():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="vault_db"
    )
    cursor = db.cursor(dictionary=True)
    return db, cursor
