import sqlite3

workwiseDatabase = "databaseWorkwise.db"

def getDatabase() -> sqlite3.Connection:
    conn = sqlite3.connect(workwiseDatabase, check_same_thread = False)
    conn.row_factory = sqlite3.Row
    return conn

def initDatabase() -> None:
    conn = getDatabase()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        username       TEXT UNIQUE NOT NULL,
        email          TEXT UNIQUE NOT NULL,
        password_hash  TEXT NOT NULL,
        role           TEXT NOT NULL DEFAULT 'user',
        created_at     TEXT NOT NULL,
        is_active      INTEGER NOT NULL DEFAULT 1
    )
    """)
    conn.commit()
    conn.close()

def userExists(conn: sqlite3.Connection, username: str, email: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = ? OR email = ?", (username, email))
    return cur.fetchone() is not None

def getUsersDetails(conn: sqlite3.Connection, uore: str):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ? OR email = ?", (uore, uore))
    return cur.fetchone()
