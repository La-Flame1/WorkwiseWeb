import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import os


# =====================================================
#  DATABASE PATH INITIALISATION (LOCAL + RAILWAY SAFE)
# =====================================================

def resolve_database_path() -> str:
    if os.environ.get("RAILWAY_ENVIRONMENT"): 
        return "/data/databaseWorkwise.db"

    project_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(project_dir, "databaseWorkwise.db")


workwiseDatabase = resolve_database_path()
db_dir = os.path.dirname(workwiseDatabase)

if not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

if not os.access(db_dir, os.W_OK):
    raise PermissionError(f"Cannot write to database directory: {db_dir}")


# =====================================================
#  GET DATABASE CONNECTION
# =====================================================

def getDatabase() -> sqlite3.Connection:
    conn = sqlite3.connect(workwiseDatabase, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


# =====================================================
#  COLUMN CHECK / TABLE INIT HELPERS
# =====================================================

def _ensure_column_exists(cur: sqlite3.Cursor, table: str, column: str, definition: str):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


# =====================================================
#  INITIAL DATABASE CREATION AND POPULATION
# =====================================================

def initDatabase() -> None:
    conn = getDatabase()
    cur = conn.cursor()

    # USERS TABLE
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

    for col, defn in [
        ("profile_image", "TEXT"),
        ("profile_name", "TEXT"),
        ("profile_bio", "TEXT"),
        ("phone_number", "TEXT"),
        ("location", "TEXT"),
        ("side_projects", "TEXT"),
        ("updated_at", "TEXT")
    ]:
        _ensure_column_exists(cur, "users", col, defn)

    # CVS
    cur.execute("""
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
    """)

    # QUALIFICATIONS
    cur.execute("""
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
    """)

    # JOB APPLICATIONS
    cur.execute("""
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
    """)

    # SAVED JOBS
    cur.execute("""
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
    """)

    # BUSINESSES
    cur.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            business_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            industry      TEXT,
            description   TEXT,
            website       TEXT,
            address       TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    """)

    # JOBS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            job_title       TEXT NOT NULL,
            description     TEXT NOT NULL,
            requirements    TEXT,
            salary_range    TEXT,
            location        TEXT,
            work_arrangement TEXT,
            employment_type TEXT,
            date_posted     TEXT DEFAULT (datetime('now')),
            is_active       INTEGER DEFAULT 1,
            FOREIGN KEY (business_id) REFERENCES businesses (business_id) ON DELETE CASCADE
        )
    """)

    # UNIONS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS unions (
            union_id INTEGER PRIMARY KEY AUTOINCREMENT,
            register_num TEXT UNIQUE NOT NULL,
            sector_info TEXT NOT NULL,
            membership_size INTEGER DEFAULT 0,
            is_active_council INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # UNION MEMBERS
    cur.execute("""
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
    """)

    cur.execute("SELECT COUNT(*) FROM jobs")
    job_count = cur.fetchone()[0]

    if job_count == 0:
        _populate_initial_data(conn)

    conn.commit()
    conn.close()


# =====================================================
#  POPULATE JOB / BUSINESS DATA (OPTION A)
# =====================================================

def _populate_initial_data(conn: sqlite3.Connection):
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO businesses (name, industry, description, website, address)
            VALUES ('Standard Bank', 'Finance', 'Leading African financial services group.',
            'https://www.standardbank.co.za', '5 Simmonds Street, Johannesburg, 2001')
        """)
        cur.execute("""
            INSERT INTO jobs (business_id, job_title, description, requirements, salary_range,
            location, employment_type, work_arrangement)
            VALUES (1, 'Financial Analyst',
            'Analyze financial data and provide strategic insights.',
            'BCom in Finance. 2+ years experience.',
            'R450,000 - R600,000 PA', 'Johannesburg, Gauteng', 'Full-time', 'Hybrid')
        """)

        cur.execute("""
            INSERT INTO businesses (name, industry, description, website, address)
            VALUES ('MTN Group', 'Telecommunications', 'Leading emerging market mobile operator.',
            'https://www.mtn.com', '216 14th Ave, Fairland, Johannesburg, 2195')
        """)
        cur.execute("""
            INSERT INTO jobs (business_id, job_title, description, requirements, salary_range,
            location, employment_type, work_arrangement)
            VALUES (2, 'Network Engineer',
            'Maintain and optimize core network infrastructure.',
            'BSc in Computer Science. CCNP certified.',
            'R500,000 - R750,000 PA', 'Johannesburg, Gauteng', 'Full-time', 'On-site')
        """)

        conn.commit()
    except Exception as e:
        print("Error populating initial data:", e)
        conn.rollback()


# =====================================================
#  USER FUNCTIONS
# =====================================================

def userExists(conn: sqlite3.Connection, username: str, email: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = ? OR email = ?", (username, email))
    return cur.fetchone() is not None


def getUsersDetails(conn: sqlite3.Connection, uore: str) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, username, email, password_hash, role
        FROM users WHERE username = ? OR email = ?
    """, (uore, uore))
    row = cur.fetchone()
    if not row:
        return None

    d = dict(row)
    d["id"] = d.pop("user_id")
    return d


def getUserById(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, username, email, role,
               profile_image, profile_name, profile_bio,
               phone_number, location, side_projects,
               created_at, updated_at
        FROM users WHERE user_id = ?
    """, (user_id,))
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


def updateUserProfile(conn: sqlite3.Connection, profile_data: Dict[str, Any]) -> bool:
    cur = conn.cursor()
    fields: List[str] = []
    values: List[Any] = []

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
            fields.append(f"{db_key} = ?")
            values.append(profile_data[api_key])

    if 'updatedAt' in profile_data:
        fields.append("updated_at = ?")
        values.append(profile_data['updatedAt'])

    if not fields:
        return False

    user_id = profile_data.get("userId")
    if not user_id:
        return False

    values.append(user_id)
    query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?"
    cur.execute(query, tuple(values))
    conn.commit()
    return cur.rowcount > 0


# =====================================================
#  CVS
# =====================================================

def getUserCVs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT cv_id, user_id, cv_name, file_path, file_size,
               mime_type, is_primary, uploaded_at
        FROM cvs WHERE user_id = ?
        ORDER BY uploaded_at DESC
    """, (user_id,))

    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []

    for row in rows:
        d = dict(zip(columns, row))
        result.append({
            "cvId": d["cv_id"],
            "userId": d["user_id"],
            "cvName": d["cv_name"],
            "filePath": d["file_path"],
            "fileSize": d.get("file_size"),
            "mimeType": d.get("mime_type"),
            "isPrimary": bool(d["is_primary"]),
            "uploadedAt": d["uploaded_at"],
        })

    return result


def addCV(conn: sqlite3.Connection, cv_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cvs
        (user_id, cv_name, file_path, file_size, mime_type, is_primary, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        cv_data["userId"],
        cv_data["cvName"],
        cv_data["filePath"],
        cv_data.get("fileSize"),
        cv_data.get("mimeType"),
        cv_data.get("isPrimary", False),
        cv_data.get("uploadedAt", datetime.now(timezone.utc).isoformat()),
    ))
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


# =====================================================
#  QUALIFICATIONS
# =====================================================

def getUserQualifications(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT qualification_id, user_id, qualification_type, institution,
               field_of_study, qualification_name, start_date, end_date,
               is_current, grade_or_gpa, description, created_at
        FROM qualifications
        WHERE user_id = ?
        ORDER BY end_date DESC NULLS LAST, start_date DESC
    """, (user_id,))

    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []

    for row in rows:
        d = dict(zip(columns, row))
        result.append({
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

    return result


def addQualification(conn: sqlite3.Connection, qual_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO qualifications
        (user_id, qualification_type, institution, field_of_study,
         qualification_name, start_date, end_date, is_current,
         grade_or_gpa, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        qual_data["userId"],
        qual_data["qualificationType"],
        qual_data["institution"],
        qual_data.get("FieldOfStudy"),
        qual_data["qualificationName"],
        qual_data.get("startDate"),
        qual_data.get("endDate"),
        int(qual_data.get("isCurrent", False)),
        qual_data.get("gradeOrGpa"),
        qual_data.get("description"),
        qual_data.get("createdAt", datetime.now(timezone.utc).isoformat()),
    ))
    conn.commit()
    return cur.lastrowid


def updateQualification(conn: sqlite3.Connection, qualification_id: int, user_id: int, qual_data: Dict[str, Any]) -> bool:
    cur = conn.cursor()
    fields: List[str] = []
    values: List[Any] = []

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

    for api_key, db_key in field_map.items():
        if api_key in qual_data:
            fields.append(f"{db_key} = ?")
            values.append(qual_data[api_key] if api_key != "isCurrent" else int(qual_data[api_key]))

    if not fields:
        return False

    values.extend([qualification_id, user_id])
    query = f"UPDATE qualifications SET {', '.join(fields)} WHERE qualification_id = ? AND user_id = ?"
    cur.execute(query, tuple(values))
    conn.commit()
    return cur.rowcount > 0


def deleteQualification(conn: sqlite3.Connection, qualification_id: int, user_id: int) -> bool:
    cur = conn.cursor()
    cur.execute("DELETE FROM qualifications WHERE qualification_id = ? AND user_id = ?", (qualification_id, user_id))
    conn.commit()
    return cur.rowcount > 0


# =====================================================
#  USER JOB APPLICATION / SAVED JOB COUNTS
# =====================================================

def getUserApplicationsCount(conn: sqlite3.Connection, user_id: int) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM job_applications WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 0


def getUserSavedJobsCount(conn: sqlite3.Connection, user_id: int) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM saved_jobs WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 0


# =====================================================
#  SAVED JOBS
# =====================================================

def getSavedJobs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT saved_job_id, user_id, job_title, company_name,
               job_location, salary_range, job_description, saved_at
        FROM saved_jobs
        WHERE user_id = ?
        ORDER BY saved_at DESC
    """, (user_id,))

    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []

    for row in rows:
        d = dict(zip(columns, row))
        result.append({
            "savedJobId": d["saved_job_id"],
            "userId": d["user_id"],
            "jobTitle": d["job_title"],
            "companyName": d["company_name"],
            "jobLocation": d.get("job_location"),
            "salaryRange": d.get("salary_range"),
            "jobDescription": d.get("job_description"),
            "savedAt": d["saved_at"],
        })

    return result


def addSavedJob(conn: sqlite3.Connection, job_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO saved_jobs
        (user_id, job_title, company_name, job_location, salary_range,
         job_description, saved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        job_data["userId"],
        job_data["jobTitle"],
        job_data["companyName"],
        job_data.get("jobLocation"),
        job_data.get("salaryRange"),
        job_data.get("jobDescription"),
        job_data.get("savedAt", datetime.now(timezone.utc).isoformat()),
    ))
    conn.commit()
    return cur.lastrowid


def deleteSavedJob(conn: sqlite3.Connection, saved_job_id: int, user_id: int) -> bool:
    cur = conn.cursor()
    cur.execute("DELETE FROM saved_jobs WHERE saved_job_id = ? AND user_id = ?", (saved_job_id, user_id))
    conn.commit()
    return cur.rowcount > 0


# =====================================================
#  BUSINESS + JOB CREATION
# =====================================================

def addBusiness(conn: sqlite3.Connection, biz_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO businesses
        (name, industry, description, website, address, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        biz_data["name"],
        biz_data.get("industry"),
        biz_data.get("description"),
        biz_data.get("website"),
        biz_data.get("address"),
        biz_data.get("createdAt", datetime.now(timezone.utc).isoformat()),
    ))
    conn.commit()
    return cur.lastrowid


def addJob(conn: sqlite3.Connection, job_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO jobs
        (business_id, job_title, description, requirements,
         salary_range, location, work_arrangement, employment_type,
         date_posted, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_data["businessId"],
        job_data["jobTitle"],
        job_data["description"],
        job_data.get("requirements"),
        job_data.get("salaryRange"),
        job_data.get("location"),
        job_data.get("workArrangement"),
        job_data.get("employmentType"),
        job_data.get("datePosted", datetime.now(timezone.utc).isoformat()),
        int(job_data.get("isActive", True)),
    ))
    conn.commit()
    return cur.lastrowid


# =====================================================
#  JOB READ FUNCTIONS
# =====================================================

def getActiveJobs(conn: sqlite3.Connection, limit: int, offset: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT j.job_id, j.job_title, j.description, j.requirements,
               j.salary_range, j.location, j.work_arrangement, j.employment_type,
               j.date_posted, j.business_id,
               b.name AS business_name, b.address AS business_address,
               b.website AS business_website
        FROM jobs j
        JOIN businesses b ON j.business_id = b.business_id
        WHERE j.is_active = 1
        ORDER BY j.date_posted DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))

    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []

    for row in rows:
        d = dict(zip(columns, row))
        result.append({
            "jobId": d["job_id"],
            "jobTitle": d["job_title"],
            "description": d["description"],
            "requirements": d.get("requirements"),
            "salaryRange": d.get("salary_range"),
            "location": d.get("location"),
            "workArrangement": d.get("work_arrangement"),
            "employmentType": d.get("employment_type"),
            "datePosted": d["date_posted"],
            "businessId": d["business_id"],
            "businessName": d.get("business_name"),
            "businessAddress": d.get("business_address"),
            "businessWebsite": d.get("business_website"),
        })

    return result


def getJobById(conn: sqlite3.Connection, job_id: int) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT
            j.job_id, j.job_title, j.description, j.requirements,
            j.salary_range, j.location, j.work_arrangement, j.employment_type,
            j.date_posted, j.business_id, j.is_active,
            b.name AS business_name, b.address AS business_address,
            b.website AS business_website, b.industry AS business_industry,
            b.description AS business_description
        FROM jobs j
        JOIN businesses b ON j.business_id = b.business_id
        WHERE j.job_id = ?
    """, (job_id,))

    row = cur.fetchone()
    if not row:
        return None

    d = dict(row)

    return {
        "jobId": d["job_id"],
        "jobTitle": d["job_title"],
        "description": d["description"],
        "requirements": d.get("requirements"),
        "salaryRange": d.get("salary_range"),
        "location": d.get("location"),
        "workArrangement": d.get("work_arrangement"),
        "employmentType": d.get("employment_type"),
        "datePosted": d["date_posted"],
        "isActive": bool(d["is_active"]),
        "businessId": d["business_id"],
        "businessName": d.get("business_name"),
        "businessAddress": d.get("business_address"),
        "businessWebsite": d.get("business_website"),
        "businessIndustry": d.get("business_industry"),
        "businessDescription": d.get("business_description"),
    }


# =====================================================
#  JOB SEARCH
# =====================================================

def searchJobs(conn: sqlite3.Connection, query: Optional[str] = None,
               employment_type: Optional[str] = None,
               work_arrangement: Optional[str] = None,
               location: Optional[str] = None,
               limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:

    cur = conn.cursor()

    base_query = """
        SELECT
            j.job_id, j.job_title, j.description, j.requirements,
            j.salary_range, j.location, j.work_arrangement, j.employment_type,
            j.date_posted, j.business_id,
            b.name AS business_name, b.address AS business_address,
            b.website AS business_website
        FROM jobs j
        JOIN businesses b ON j.business_id = b.business_id
        WHERE j.is_active = 1
    """

    params: List[Any] = []
    result: List[Dict[str, Any]] = []

    if query:
        search_term = f"%{query.lower()}%"
        base_query += """
            AND (
                LOWER(j.job_title) LIKE ?
                OR LOWER(j.description) LIKE ?
                OR LOWER(j.requirements) LIKE ?
                OR LOWER(j.location) LIKE ?
                OR LOWER(b.name) LIKE ?
            )
        """
        params.extend([search_term] * 5)

    if employment_type:
        base_query += " AND j.employment_type = ?"
        params.append(employment_type)

    if work_arrangement:
        base_query += " AND j.work_arrangement = ?"
        params.append(work_arrangement)

    if location:
        base_query += " AND LOWER(j.location) LIKE ?"
        params.append(f"%{location.lower()}%")

    base_query += " ORDER BY j.date_posted DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur.execute(base_query, tuple(params))

    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []

    for row in rows:
        d: Dict[str, Any] = dict(zip(columns, row))
        job_dict: Dict[str, Any] = {
            "jobId": d["job_id"],
            "jobTitle": d["job_title"],
            "description": d["description"],
            "requirements": d.get("requirements"),
            "salaryRange": d.get("salary_range"),
            "location": d.get("location"),
            "workArrangement": d.get("work_arrangement"),
            "employmentType": d.get("employment_type"),
            "datePosted": d["date_posted"],
            "businessId": d["business_id"],
            "businessName": d.get("business_name"),
            "businessAddress": d.get("business_address"),
            "businessWebsite": d.get("business_website"),
        }
        result.append(job_dict)

    return result


# =====================================================
#  UNIONS
# =====================================================

def unionExists(conn: sqlite3.Connection, register_num: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM unions WHERE register_num = ?", (register_num,))
    return cur.fetchone() is not None


def getUnions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM unions")

    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def createUnion(conn: sqlite3.Connection, union_data: Dict[str, Any]) -> bool:
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO unions
            (register_num, sector_info, membership_size, is_active_council, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            union_data["register_num"],
            union_data["sector_info"],
            union_data.get("membership_size", 0),
            int(union_data.get("is_active_council", False)),
            union_data.get("createdAt", datetime.now(timezone.utc).isoformat()),
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print("Error creating union:", e)
        conn.rollback()
        return False


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
    try:
        cur.execute("""
            INSERT INTO union_members
            (worker_id, union_id, membership_num, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            member_data["worker_id"],
            member_data["union_id"],
            member_data["membership_num"],
            member_data.get("status", "active"),
            member_data.get("createdAt", datetime.now(timezone.utc).isoformat()),
        ))
        conn.commit()
        return cur.lastrowid

    except sqlite3.IntegrityError:
        return None
    except Exception as e:
        print("Error adding union member:", e)
        conn.rollback()
        return None
