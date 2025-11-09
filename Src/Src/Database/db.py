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
            is_active      INTEGER NOT NULL DEFAULT 1,
            profile_image  TEXT,
            profile_name   TEXT,
            profile_bio    TEXT,
            phone_number   TEXT,
            location       TEXT,
            updated_at     TEXT
        )
    """)
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cvs (
            cv_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            cv_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            is_primary BOOLEAN DEFAULT FALSE,
            uploaded_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS qualifications (
            qualification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            qualification_type TEXT NOT NULL,
            institution TEXT NOT NULL,
            field_of_study TEXT,
            qualification_name TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            is_current BOOLEAN DEFAULT FALSE,
            grade_or_gpa TEXT,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS job_applications (
            application_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            company_name TEXT NOT NULL,
            application_date TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'pending',
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS saved_jobs (
            saved_job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            company_name TEXT NOT NULL,
            job_location TEXT,
            salary_range TEXT,
            job_description TEXT,
            saved_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')
    
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

    cur.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT NOT NULL,
            company_name TEXT NOT NULL,
            job_location TEXT,
            salary_range TEXT,
            job_description TEXT,
            employment_type TEXT,
            posted_at TEXT DEFAULT (datetime('now'))
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

def getUserById(conn: sqlite3.Connection, user_id: int):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cur.fetchone()

def updateUserProfile(conn: sqlite3.Connection, user_id: int, profile_data: Dict[str, Any]) -> bool:
    cur = conn.cursor()
    fields = []
    values = []
    
    allowed_fields = ['profile_image', 'profile_name', 'profile_bio', 'phone_number', 'location']
    for field in allowed_fields:
        if field in profile_data:
            fields.append(f"{field} = ?")
            values.append(profile_data[field])
    
    if not fields:
        return False
    
    fields.append("updated_at = ?")
    values.append(profile_data.get('updated_at'))
    values.append(user_id)
    
    query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?"
    cur.execute(query, values)
    conn.commit()
    return cur.rowcount > 0

def getUserCVs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM cvs WHERE user_id = ? ORDER BY uploaded_at DESC", (user_id,))
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def addCV(conn: sqlite3.Connection, cv_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cvs (user_id, cv_name, file_path, file_size, mime_type, is_primary, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (cv_data['user_id'], cv_data['cv_name'], cv_data['file_path'], 
          cv_data.get('file_size'), cv_data.get('mime_type'), 
          cv_data.get('is_primary', False), cv_data['uploaded_at']))
    conn.commit()
    return cur.lastrowid

def deleteCV(conn: sqlite3.Connection, cv_id: int, user_id: int) -> bool:
    cur = conn.cursor()
    cur.execute("DELETE FROM cvs WHERE cv_id = ? AND user_id = ?", (cv_id, user_id))
    conn.commit()
    return cur.rowcount > 0

def setPrimaryCV(conn: sqlite3.Connection, cv_id: int, user_id: int) -> bool:
    cur = conn.cursor()

    cur.execute("UPDATE cvs SET is_primary = 0 WHERE user_id = ?", (user_id,))

    cur.execute("UPDATE cvs SET is_primary = 1 WHERE cv_id = ? AND user_id = ?", (cv_id, user_id))
    conn.commit()
    return cur.rowcount > 0

def getUserQualifications(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM qualifications WHERE user_id = ? ORDER BY end_date DESC, start_date DESC", (user_id,))
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def addQualification(conn: sqlite3.Connection, qual_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO qualifications (user_id, qualification_type, institution, field_of_study, 
                                   qualification_name, start_date, end_date, is_current, 
                                   grade_or_gpa, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (qual_data['user_id'], qual_data['qualification_type'], qual_data['institution'],
          qual_data.get('field_of_study'), qual_data['qualification_name'],
          qual_data.get('start_date'), qual_data.get('end_date'), 
          qual_data.get('is_current', False), qual_data.get('grade_or_gpa'),
          qual_data.get('description'), qual_data['created_at']))
    conn.commit()
    return cur.lastrowid

def updateQualification(conn: sqlite3.Connection, qualification_id: int, user_id: int, qual_data: Dict[str, Any]) -> bool:
    cur = conn.cursor()
    cur.execute("""
        UPDATE qualifications 
        SET qualification_type = ?, 
            institution = ?, 
            field_of_study = ?, 
            qualification_name = ?, 
            start_date = ?, 
            end_date = ?, 
            is_current = ?, 
            grade_or_gpa = ?,
            description = ?
        WHERE qualification_id = ? AND user_id = ?
    """, (qual_data['qualification_type'], qual_data['institution'], 
          qual_data.get('field_of_study'), qual_data['qualification_name'],
          qual_data.get('start_date'), qual_data.get('end_date'),
          qual_data.get('is_current', False), qual_data.get('grade_or_gpa'),
          qual_data.get('description'), qualification_id, user_id))
    conn.commit()
    return cur.rowcount > 0

def deleteQualification(conn: sqlite3.Connection, qualification_id: int, user_id: int) -> bool:
    cur = conn.cursor()
    cur.execute("DELETE FROM qualifications WHERE qualification_id = ? AND user_id = ?", (qualification_id, user_id))
    conn.commit()
    return cur.rowcount > 0

def getUserApplicationsCount(conn: sqlite3.Connection, user_id: int) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM job_applications WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    return result[0] if result else 0

def getUserSavedJobsCount(conn: sqlite3.Connection, user_id: int) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM saved_jobs WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    return result[0] if result else 0

def getSavedJobs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM saved_jobs WHERE user_id = ? ORDER BY saved_at DESC", (user_id,))
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def addSavedJob(conn: sqlite3.Connection, job_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO saved_jobs (user_id, job_title, company_name, job_location, 
                               salary_range, job_description, saved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (job_data['user_id'], job_data['job_title'], job_data['company_name'],
          job_data.get('job_location'), job_data.get('salary_range'),
          job_data.get('job_description'), job_data['saved_at']))
    conn.commit()
    return cur.lastrowid

def deleteSavedJob(conn: sqlite3.Connection, saved_job_id: int, user_id: int) -> bool:
    cur = conn.cursor()
    cur.execute("DELETE FROM saved_jobs WHERE saved_job_id = ? AND user_id = ?", (saved_job_id, user_id))
    conn.commit()
    return cur.rowcount > 0

# Union functions (existing)
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
    """, (union_data['register_num'], union_data['sector_info'], union_data['membership_size'], 
          union_data['is_active_council'], union_data['created_at']))
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
    """, (member_data['worker_id'], member_data['union_id'], member_data['membership_num'], 
          member_data['status'], member_data['created_at']))
    conn.commit()
    return cur.lastrowid

def getRandomJobs(conn: sqlite3.Connection, limit: int = 20):
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM jobs ORDER BY RANDOM() LIMIT ?",
        (limit,)
    )
    columns = [d[0] for d in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def getJobById(conn: sqlite3.Connection, job_id: int):
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    row = cur.fetchone()
    if not row:
        return None
    columns = [d[0] for d in cur.description]
    return dict(zip(columns, row))

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import sqlite3

def createPasswordResetToken(conn: sqlite3.Connection, user_id: int, email: str, reset_code: str) -> Optional[int]:
    """
    Create a password reset token
    
    Args:
        conn: Database connection
        user_id: User ID
        email: User email
        reset_code: 6-digit reset code
        
    Returns:
        Token ID if successful, None otherwise
    """
    cur = conn.cursor()
    
    # Calculate expiration (15 minutes from now)
    created_at = datetime.now(timezone.utc).isoformat()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    
    cur.execute("""
        INSERT INTO password_reset_tokens (user_id, email, reset_code, created_at, expires_at, used)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (user_id, email, reset_code, created_at, expires_at))
    
    conn.commit()
    return cur.lastrowid

def getUserByEmail(conn: sqlite3.Connection, email: str):
    """Get user by email address"""
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    return cur.fetchone()

def verifyResetCode(conn: sqlite3.Connection, email: str, reset_code: str) -> Optional[Dict[str, Any]]:
    """
    Verify if a reset code is valid and not expired
    
    Args:
        conn: Database connection
        email: User email
        reset_code: 6-digit reset code
        
    Returns:
        Token data if valid, None otherwise
    """
    cur = conn.cursor()
    
    # Get the most recent unused token for this email and code
    cur.execute("""
        SELECT * FROM password_reset_tokens 
        WHERE email = ? AND reset_code = ? AND used = 0
        ORDER BY created_at DESC
        LIMIT 1
    """, (email, reset_code))
    
    token = cur.fetchone()
    
    if not token:
        return None
    
    # Check if token is expired
    expires_at = datetime.fromisoformat(token["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        return None
    
    # Return token data as dict
    return dict(token)

def markResetTokenAsUsed(conn: sqlite3.Connection, token_id: int) -> bool:
    """Mark a reset token as used"""
    cur = conn.cursor()
    cur.execute("UPDATE password_reset_tokens SET used = 1 WHERE token_id = ?", (token_id,))
    conn.commit()
    return cur.rowcount > 0

def updateUserPassword(conn: sqlite3.Connection, user_id: int, new_password_hash: str) -> bool:
    """
    Update user's password
    
    Args:
        conn: Database connection
        user_id: User ID
        new_password_hash: New hashed password
        
    Returns:
        True if successful, False otherwise
    """
    cur = conn.cursor()
    updated_at = datetime.now(timezone.utc).isoformat()
    
    cur.execute("""
        UPDATE users 
        SET password_hash = ?, updated_at = ?
        WHERE user_id = ?
    """, (new_password_hash, updated_at, user_id))
    
    conn.commit()
    return cur.rowcount > 0

def cleanupExpiredResetTokens(conn: sqlite3.Connection) -> int:
    """
    Delete expired reset tokens (older than 24 hours)
    
    Returns:
        Number of tokens deleted
    """
    cur = conn.cursor()
    cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    
    cur.execute("""
        DELETE FROM password_reset_tokens 
        WHERE created_at < ?
    """, (cutoff_time,))
    
    conn.commit()
    return cur.rowcount
