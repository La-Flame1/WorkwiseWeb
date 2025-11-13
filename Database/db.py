# Database/db.py
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime

workwiseDatabase = "databaseWorkwise.db"


def getDatabase() -> sqlite3.Connection:
    conn = sqlite3.connect(workwiseDatabase, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


# ----------------------------------------------------------------------
#  DATABASE INITIALISATION + SAFE MIGRATION
# ----------------------------------------------------------------------
def _ensure_column_exists(cur: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    """Add column if it does not exist – safe to call on every start."""
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def initDatabase() -> None:
    conn = getDatabase()
    cur = conn.cursor()

    # ---- USERS -------------------------------------------------------
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
            side_projects  TEXT,
            updated_at     TEXT
        )
    """)

    # ---- MIGRATE MISSING PROFILE COLUMNS -----------------------------
    for col, defn in [
        ("profile_image", "TEXT"),
        ("profile_name", "TEXT"),
        ("profile_bio", "TEXT"),
        ("phone_number", "TEXT"),
        ("location", "TEXT"),
        ("side_projects", "TEXT"),
        ("updated_at", "TEXT"),
    ]:
        _ensure_column_exists(cur, "users", col, defn)

    # ---- CVS ---------------------------------------------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cvs (
            cv_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            cv_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,
            is_primary INTEGER DEFAULT 0,
            uploaded_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')

    # ---- QUALIFICATIONS ---------------------------------------------
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
            is_current INTEGER DEFAULT 0,
            grade_or_gpa TEXT,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')

    # ---- JOB APPLICATIONS -------------------------------------------
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

    # ---- SAVED JOBS -------------------------------------------------
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

    # ---- UNIONS -----------------------------------------------------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS unions (
            union_id INTEGER PRIMARY KEY AUTOINCREMENT,
            register_num TEXT UNIQUE NOT NULL,
            sector_info TEXT NOT NULL,
            membership_size INTEGER DEFAULT 0,
            is_active_council INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')

    # ---- UNION MEMBERS -----------------------------------------------
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


# ----------------------------------------------------------------------
#  PUBLIC HELPERS (used from main.py)
# ----------------------------------------------------------------------
def userExists(conn: sqlite3.Connection, username: str, email: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = ? OR email = ?", (username, email))
    return cur.fetchone() is not None


# ---------- LOGIN ----------
def getUsersDetails(conn: sqlite3.Connection, uore: str) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, username, email, password_hash, role "
        "FROM users WHERE username = ? OR email = ?",
        (uore, uore)
    )
    row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["id"] = d.pop("user_id")
    return d


# ---------- PROFILE ----------
def getUserById(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """SELECT user_id, username, email, role,
                  profile_image, profile_name, profile_bio,
                  phone_number, location, side_projects,
                  created_at, updated_at
           FROM users WHERE user_id = ?""",
        (user_id,)
    )
    row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    return {
        "userId": d["user_id"],
        "username": d["username"],
        "email": d["email"],
        "role": d["role"],
        "profileImage": d.get("profile_image"),
        "profileName": d.get("profile_name"),
        "profileBio": d.get("profile_bio"),
        "phoneNumber": d.get("phone_number"),
        "location": d.get("location"),
        "sideProjects": d.get("side_projects"),
        "createdAt": d["created_at"],
        "updatedAt": d.get("updated_at"),
    }


# Database/db.py
def updateUserProfile(conn: sqlite3.Connection, profile_data: Dict[str, Any]) -> bool:
    cur = conn.cursor()
    fields = []
    values = []

    field_map = {
        'profileName': 'profile_name',
        'profileBio': 'profile_bio',
        'phoneNumber': 'phone_number',
        'location': 'location',
        'sideProjects': 'side_projects',
        'profileImage': 'profile_image'
    }

    for api_key, db_key in field_map.items():
        if api_key in profile_data:
            fields.append(f"{db_key} = ?") # type: ignore
            values.append(profile_data[api_key]) # type: ignore

    if 'updatedAt' in profile_data:
        fields.append("updated_at = ?") # type: ignore
        values.append(profile_data['updatedAt']) # type: ignore

    if not fields:
        return False

    # Use the user_id from the route (not passed in profile_data)
    user_id = profile_data.get("userId")
    if not user_id:
        return False

    values.append(user_id) # type: ignore
    query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?" # type: ignore
    cur.execute(query, values) # type: ignore
    conn.commit()
    return cur.rowcount > 0

# ----------------------------------------------------------------------
#  CV HELPERS (internal names start with _ to avoid clash with route)
# ----------------------------------------------------------------------
def _getUserCVs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """SELECT cv_id, user_id, cv_name, file_path, file_size,
                  mime_type, is_primary, uploaded_at
           FROM cvs WHERE user_id = ? ORDER BY uploaded_at DESC""",
        (user_id,),
    )
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    result = []
    for row in rows:
        d = dict(zip(columns, row))
        result.append({ # type: ignore
            "cvId": d["cv_id"],
            "userId": d["user_id"],
            "cvName": d["cv_name"],
            "filePath": d["file_path"],
            "fileSize": d.get("file_size"),
            "mimeType": d.get("mime_type"),
            "isPrimary": bool(d["is_primary"]),
            "uploadedAt": d["uploaded_at"],
        })
    return result # type: ignore


def getUserCVs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    """Public wrapper – called from main.py."""
    return _getUserCVs(conn, user_id)


def addCV(conn: sqlite3.Connection, cv_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO cvs
           (user_id, cv_name, file_path, file_size, mime_type, is_primary, uploaded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            cv_data["userId"],
            cv_data["cvName"],
            cv_data["filePath"],
            cv_data.get("fileSize"),
            cv_data.get("mimeType"),
            cv_data.get("isPrimary", False),
            cv_data.get("uploadedAt", datetime.utcnow().isoformat()), # type: ignore
        ),
    )
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
    cur.execute(
        "UPDATE cvs SET is_primary = 1 WHERE cv_id = ? AND user_id = ?", (cv_id, user_id)
    )
    conn.commit()
    return cur.rowcount > 0


# ----------------------------------------------------------------------
#  QUALIFICATIONS
# ----------------------------------------------------------------------
def _getUserQualifications(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """SELECT qualification_id, user_id, qualification_type, institution,
                  field_of_study, qualification_name, start_date, end_date,
                  is_current, grade_or_gpa, description, created_at
           FROM qualifications
           WHERE user_id = ?
           ORDER BY end_date DESC NULLS LAST, start_date DESC""",
        (user_id,),
    )
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    result = []
    for row in rows:
        d = dict(zip(columns, row))
        result.append({ # type: ignore
            "qualificationId": d["qualification_id"],
            "userId": d["user_id"],
            "qualificationType": d["qualification_type"],
            "institution": d["institution"],
            "fieldOfStudy": d.get("field_of_study"),
            "qualificationName": d["qualification_name"],
            "startDate": d.get("start_date"),
            "endDate": d.get("end_date"),
            "isCurrent": bool(d["is_current"]),
            "gradeOrGpa": d.get("grade_or_gpa"),
            "description": d.get("description"),
            "createdAt": d["created_at"],
        })
    return result # type: ignore


def getUserQualifications(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    return _getUserQualifications(conn, user_id)


def addQualification(conn: sqlite3.Connection, qual_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO qualifications
           (user_id, qualification_type, institution, field_of_study,
            qualification_name, start_date, end_date, is_current,
            grade_or_gpa, description, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            qual_data["userId"],
            qual_data["qualificationType"],
            qual_data["institution"],
            qual_data.get("fieldOfStudy"),
            qual_data["qualificationName"],
            qual_data.get("startDate"),
            qual_data.get("endDate"),
            qual_data.get("isCurrent", False),
            qual_data.get("gradeOrGpa"),
            qual_data.get("description"),
            qual_data.get("createdAt", datetime.utcnow().isoformat()), # type: ignore
        ),
    )
    conn.commit()
    return cur.lastrowid


def updateQualification(
    conn: sqlite3.Connection,
    qualification_id: int,
    user_id: int,
    qual_data: Dict[str, Any],
) -> bool:
    cur = conn.cursor()
    fields = []
    values = []
    field_map = {
        "qualificationType": "qualification_type",
        "institution": "institution",
        "fieldOfStudy": "field_of_study",
        "qualificationName": "qualification_name",
        "startDate": "start_date",
        "endDate": "end_date",
        "isCurrent": "is_current",
        "gradeOrGpa": "grade_or_gpa",
        "description": "description",
    }
    for api, db in field_map.items():
        if api in qual_data:
            fields.append(f"{db} = ?") # type: ignore
            values.append(qual_data[api]) # type: ignore

    if not fields:
        return False

    values.extend([qualification_id, user_id]) # type: ignore
    query = f"UPDATE qualifications SET {', '.join(fields)} WHERE qualification_id = ? AND user_id = ?" # type: ignore
    cur.execute(query, values) # type: ignore
    conn.commit()
    return cur.rowcount > 0


def deleteQualification(conn: sqlite3.Connection, qualification_id: int, user_id: int) -> bool:
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM qualifications WHERE qualification_id = ? AND user_id = ?",
        (qualification_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0


# ----------------------------------------------------------------------
#  STATS & SAVED JOBS
# ----------------------------------------------------------------------
def getUserApplicationsCount(conn: sqlite3.Connection, user_id: int) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM job_applications WHERE user_id = ?", (user_id,))
    return cur.fetchone()[0]


def getUserSavedJobsCount(conn: sqlite3.Connection, user_id: int) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM saved_jobs WHERE user_id = ?", (user_id,))
    return cur.fetchone()[0]


def _getSavedJobs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """SELECT saved_job_id, user_id, job_title, company_name,
                  job_location, salary_range, job_description, saved_at
           FROM saved_jobs
           WHERE user_id = ? ORDER BY saved_at DESC""",
        (user_id,),
    )
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    result = []
    for row in rows:
        d = dict(zip(columns, row))
        result.append({ # type: ignore
            "savedJobId": d["saved_job_id"],
            "userId": d["user_id"],
            "jobTitle": d["job_title"],
            "companyName": d["company_name"],
            "jobLocation": d.get("job_location"),
            "salaryRange": d.get("salary_range"),
            "jobDescription": d.get("job_description"),
            "savedAt": d["saved_at"],
        })
    return result # type: ignore


def getSavedJobs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    return _getSavedJobs(conn, user_id)


def addSavedJob(conn: sqlite3.Connection, job_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO saved_jobs
           (user_id, job_title, company_name, job_location,
            salary_range, job_description, saved_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            job_data["userId"],
            job_data["jobTitle"],
            job_data["companyName"],
            job_data.get("jobLocation"),
            job_data.get("salaryRange"),
            job_data.get("jobDescription"),
            job_data.get("savedAt", datetime.utcnow().isoformat()), # type: ignore
        ),
    )
    conn.commit()
    return cur.lastrowid


def deleteSavedJob(conn: sqlite3.Connection, saved_job_id: int, user_id: int) -> bool:
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM saved_jobs WHERE saved_job_id = ? AND user_id = ?",
        (saved_job_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0


# ----------------------------------------------------------------------
#  UNION HELPERS
# ----------------------------------------------------------------------
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
    cur.execute(
        """INSERT INTO unions
           (register_num, sector_info, membership_size, is_active_council, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (
            union_data["register_num"],
            union_data["sector_info"],
            union_data.get("membership_size", 0),
            union_data.get("is_active_council", False),
            union_data.get("createdAt", datetime.utcnow().isoformat()), # type: ignore
        ),
    )
    conn.commit()
    return cur.lastrowid


def workerInUnion(conn: sqlite3.Connection, worker_id: int, union_id: int) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM union_members WHERE worker_id = ? AND union_id = ?",
        (worker_id, union_id),
    )
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
    cur.execute(
        """INSERT INTO union_members
           (worker_id, union_id, membership_num, status, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (
            member_data["worker_id"],
            member_data["union_id"],
            member_data["membership_num"],
            member_data.get("status", "active"),
            member_data.get("createdAt", datetime.utcnow().isoformat()), # type: ignore
        ),
    )
    conn.commit()
    return cur.lastrowid