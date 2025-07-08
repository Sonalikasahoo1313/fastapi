import mysql.connector

# ------------------ Global Tiffin DB Connection ------------------
def get_global_tiffin_db_connection():
    db = mysql.connector.connect(
        host="srv1132.hstgr.io",
        user="u929798141_essar",
        password="Essar!@#123",
        database="u929798141_globaltiffin"
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
