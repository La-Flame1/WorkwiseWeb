import sqlite3
from typing import List, Dict, Any, Optional

workwiseDatabase = "databaseWorkwise.db"

def getDatabase() -> sqlite3.Connection:
    conn = sqlite3.connect(workwiseDatabase, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
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
    cur.execute('''
        CREATE TABLE IF NOT EXISTS unions (
            union_id INTEGER PRIMARY KEY AUTOINCREMENT,
            register_num TEXT UNIQUE NOT NULL,
            sector_info TEXT NOT NULL,
            membership_size INTEGER DEFAULT 0,
            is_active_council BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS union_members (
            membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL,
            union_id INTEGER NOT NULL,
            membership_num TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (worker_id) REFERENCES users (user_id) ON DELETE CASCADE,
            FOREIGN KEY (union_id) REFERENCES unions (union_id) ON DELETE CASCADE,
            UNIQUE (worker_id, union_id)
        )
    ''')
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

def unionExists(conn: sqlite3.Connection, register_num: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM unions WHERE register_num = ?", (register_num,))
    return cur.fetchone() is not None

def getUnions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM unions")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def createUnion(conn: sqlite3.Connection, union_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO unions (register_num, sector_info, membership_size, is_active_council, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (union_data['register_num'], union_data['sector_info'], union_data['membership_size'], union_data['is_active_council'], union_data['created_at']))
    conn.commit()
    return cur.lastrowid

def workerInUnion(conn: sqlite3.Connection, worker_id: int, union_id: int) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM union_members WHERE worker_id = ? AND union_id = ?", (worker_id, union_id))
    return cur.fetchone() is not None

def getUnionMembers(conn: sqlite3.Connection, union_id: Optional[int] = None) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    if union_id:
        cur.execute("SELECT * FROM union_members WHERE union_id = ?", (union_id,))
    else:
        cur.execute("SELECT * FROM union_members")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]
    
def addUnionMember(conn: sqlite3.Connection, member_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO union_members (worker_id, union_id, membership_num, status, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (member_data['worker_id'], member_data['union_id'], member_data['membership_num'], member_data['status'], member_data['created_at']))
    conn.commit()
    return cur.lastrowid
