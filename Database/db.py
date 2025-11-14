# Database/db.py
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import os 
import random # <-- 1. ADD THIS IMPORT
import string # <-- 2. ADD THIS IMPORT

# --- This path logic is robust for both local and Railway ---
def _resolve_database_path() -> str:
    """Determine database path based on server/environment.

    Resolution order (first match wins):
    1. Explicit override via WORKWISE_DB_PATH env.
    2. Railway: RAILWAY_ENVIRONMENT -> /data/databaseWorkwise.db
    3. Generic production/staging via ENV env var -> /var/lib/workwise/databaseWorkwise.db (ensure dir).
    4. Hostname heuristic (starts with 'prod', 'web', 'api') -> /var/lib/workwise/databaseWorkwise.db
    5. Fallback to user home: ~/.workwise/databaseWorkwise.db
    """
    override = os.environ.get("WORKWISE_DB_PATH")
    if override:
        return override

    if os.environ.get("RAILWAY_ENVIRONMENT"):
        return "/data/databaseWorkwise.db"

    env = (os.environ.get("ENV") or os.environ.get("APP_ENV") or "").lower()
    hostname = os.environ.get("HOSTNAME", "").lower()
    prod_like = hostname.startswith(("prod", "web", "api")) or env in {"production", "staging"}
    if prod_like:
        base_dir = "/var/lib/workwise"
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception:
            # If we cannot create system dir (e.g. insufficient permissions), fallback to home.
            base_dir = os.path.join(os.path.expanduser("~"), ".workwise")
            os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, "databaseWorkwise.db")

    # Local/dev fallback
    home_dir = os.path.expanduser("~")
    app_data_dir = os.path.join(home_dir, ".workwise")
    os.makedirs(app_data_dir, exist_ok=True)
    return os.path.join(app_data_dir, "databaseWorkwise.db")


print("--- DETERMINING DATABASE PATH ---")
workwiseDatabase = _resolve_database_path()
print(f"Using database path: {workwiseDatabase}")
print("---------------------------------")
# --- End path logic ---


def getDatabase() -> sqlite3.Connection:
    conn = sqlite3.connect(workwiseDatabase, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# ----------------------------------------------------------------------
#  DATABASE INITIALISATION + SAFE MIGRATION
# ----------------------------------------------------------------------
def _ensure_column_exists(cur: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    if column not in cols:
        print(f"Adding column {column} to {table}...")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def initDatabase() -> None:
    print("Initializing database...")
    conn = getDatabase()
    cur = conn.cursor()

    # ---- USERS ----
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
    for col, defn in [("profile_image", "TEXT"), ("profile_name", "TEXT"), ("profile_bio", "TEXT"), ("phone_number", "TEXT"), ("location", "TEXT"), ("side_projects", "TEXT"), ("updated_at", "TEXT")]:
        _ensure_column_exists(cur, "users", col, defn)

    # ---- CVS ----
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

    # ---- QUALIFICATIONS ----
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

    # ---- JOB APPLICATIONS ----
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

    # ---- SAVED JOBS ----
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

    # ---- BUSINESSES ----
    cur.execute('''
        CREATE TABLE IF NOT EXISTS businesses (
            business_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            industry      TEXT,
            description   TEXT,
            website       TEXT,
            address       TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    ''')

    # ---- JOBS ----
    cur.execute('''
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
    ''')
    
    # ---- UNIONS ----
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

    # ---- UNION MEMBERS ----
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

    # --- 3. ADD NEW TABLE FOR PASSWORD RESET CODES ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_codes (
            code_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT NOT NULL,
            code        TEXT NOT NULL,
            expires_at  TEXT NOT NULL,
            is_used     INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    ''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_email_code ON password_reset_codes (email, code, is_used)")
    # --- END NEW TABLE ---

    # --- AUTO-POPULATE DATABASE ---
    cur.execute("SELECT COUNT(*) FROM jobs")
    job_count = cur.fetchone()[0]
    
    if job_count == 0:
        print("Database is empty. Populating with initial data...")
        _populate_initial_data(conn)
        print("Initial data populated successfully.")
    else:
        print(f"Database already contains {job_count} jobs. Skipping population.")
    # --- END ---

    conn.commit()
    conn.close()
    print("Database initialization complete.")


# ----------------------------------------------------------------------
#  --- FUNCTION TO POPULATE DATABASE ---
# ----------------------------------------------------------------------
def _populate_initial_data(conn: sqlite3.Connection):
    # ... (This whole function is unchanged, keep your existing one) ...
    cur = conn.cursor()
    try:
        # 1. Standard Bank
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Standard Bank', 'Finance', 'Leading African financial services group.', 'https://www.standardbank.co.za', '5 Simmonds Street, Johannesburg, 2001')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (1, 'Financial Analyst', 'Analyze financial data and provide strategic insights.', 'BCom in Finance. 2+ years experience.', 'R450,000 - R600,000 PA', 'Johannesburg, Gauteng', 'Full-time', 'Hybrid')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (1, 'Agile Project Manager', 'Lead a 6-month digital transformation project.', 'PMP or Prince2 certified. 5+ years project management.', 'R80,000 - R110,000 PM', 'Johannesburg, Gauteng', 'Contract', 'Hybrid')""")
        
        # 2. MTN
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('MTN Group', 'Telecommunications', 'Leading emerging market mobile operator.', 'https://www.mtn.com', '216 14th Ave, Fairland, Johannesburg, 2195')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (2, 'Network Engineer', 'Maintain and optimize our core network infrastructure.', 'BSc in Computer Science. CCNP certified.', 'R500,000 - R750,000 PA', 'Johannesburg, Gauteng', 'Full-time', 'On-site')""")

        # 3. Takealot
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Takealot', 'E-commerce', 'South Africa''s largest online retailer.', 'https://www.takealot.com', '10 Rua Vasco Da Gama Plain, Cape Town, 8001')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (3, 'Senior Frontend Developer', 'Build customer-facing web applications using React.', '5+ years experience in frontend. Expert in React.js.', 'R700,000 - R900,000 PA', 'Cape Town, Western Cape', 'Hybrid')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (3, 'Weekend Delivery Driver', 'Deliver packages on Saturdays and Sundays.', 'Valid SA driver''s license. Own reliable vehicle.', 'R150 - R200 per hour', 'Cape Town, Western Cape', 'Part-time', 'Remote')""")

        # 4. Sasol
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Sasol', 'Energy & Chemicals', 'Global integrated chemicals and energy company.', 'https::/www.sasol.com', '50 Katherine Street, Sandton, Johannesburg, 2196')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (4, 'Chemical Process Engineer', 'Design and optimize chemical processes.', 'BEng/BSc in Chemical Engineering. ECSA registered.', 'R600,000 - R850,000 PA', 'Secunda, Mpumalanga', 'Full-time', 'On-site')""")

        # 5. Woolworths
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Woolworths', 'Retail', 'Quality fashion, food, and homeware.', 'https://www.woolworths.co.za', '93 Longmarket Street, Cape Town, 8001')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (5, 'Supply Chain Manager', 'Oversee the end-to-end supply chain for fresh produce.', 'BCom in Logistics. 5+ years in FMCG retail.', 'R800,000 - R1,100,000 PA', 'Cape Town, Western Cape', 'Hybrid')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (5, 'Community Garden Volunteer', 'Help maintain the community garden.', 'Passion for sustainability. 4 hours per week.', 'Unpaid (Volunteer)', 'Stellenbosch, Western Cape', 'Volunteer', 'On-site')""")

        # 6. Discovery
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Discovery', 'Insurance & Financial Services', 'Shared-value insurance provider.', 'https://www.discovery.co.za', '1 Discovery Place, Sandton, Johannesburg, 2196')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (6, 'Actuarial Specialist', 'Develop models for risk assessment and product pricing.', 'Qualified or nearly-qualified Actuary.', 'R900,000 - R1,300,000 PA', 'Sandton, Gauteng', 'Hybrid')""")

        # 7. Anglo American
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Anglo American', 'Mining', 'One of the world''s largest mining companies.', 'https://www.angloamerican.com', '44 Main Street, Marshalltown, Johannesburg, 2001')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (7, 'Geologist', 'Conduct geological mapping and resource estimation.', 'BSc (Hons) in Geology. 3+ years experience.', 'R700,000 - R950,000 PA', 'Rustenburg, North West', 'Full-time', 'On-site')""")

        # 8. Shoprite
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Shoprite Holdings', 'Retail', 'Africa''s largest food retailer.', 'https://www.shopriteholdings.co.za', 'Cnr Old Paarl Rd & Cilmor Street, Brackenfell, Cape Town, 7560')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (8, 'Retail Store Manager', 'Manage all operations of a high-volume Checkers store.', 'Matric. 5+ years in retail management.', 'R350,000 - R500,000 PA', 'Durban, KZN', 'Full-time', 'On-site')""")

        # 9. Dimension Data
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Dimension Data', 'IT Services', 'Global systems integrator.', 'https://www.dimensiondata.com', '1 Sluice Business Park, Sluice Rd, Bryanston, Johannesburg, 2191')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (9, 'Cloud Solutions Architect', 'Design and implement hybrid cloud solutions (Azure/AWS).', 'Azure/AWS certification. 5+ years experience.', 'R900,000 - R1,200,000 PA', 'Johannesburg, Gauteng', 'Full-time', 'Remote')""")

        # 10. FNB
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('First National Bank', 'Finance', 'One of South Africa''s "big four" banks.', 'https://www.fnb.co.za', '1 First Place, Bank City, Johannesburg, 2000')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (10, 'UX/UI Designer (Banking App)', 'Create user experiences for the FNB mobile app.', 'Portfolio of mobile app designs. 3+ years in UX/UI.', 'R550,000 - R700,000 PA', 'Cape Town, Western Cape', 'Full-time', 'Hybrid')""")

        # 11. MultiChoice
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('MultiChoice', 'Media & Entertainment', 'Owner of DStv and Showmax.', 'https://www.multichoice.com', '144 Bram Fischer Drive, Randburg, Johannesburg, 2194')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (11, 'Digital Marketing Specialist', 'Run performance marketing campaigns for Showmax.', 'Degree in Marketing. 3+ years in digital marketing.', 'R400,000 - R550,000 PA', 'Johannesburg, Gauteng', 'Full-time', 'Hybrid')""")

        # 12. Sanlam
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Sanlam', 'Insurance & Financial Services', 'Diversified financial services group.', 'https_www.sanlam.com', '2 Strand Road, Bellville, Cape Town, 7530')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (12, 'Data Scientist', 'Use machine learning to model customer behavior.', 'MSc in Data Science/Stats. 2+ years experience. Python, R, SQL.', 'R650,000 - R850,000 PA', 'Cape Town, Western Cape', 'Full-time', 'Hybrid')""")

        # 13. Capitec Bank
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Capitec Bank', 'Finance', 'South African retail bank.', 'https://www.capitecbank.co.za', '5 Neutron Street, Techno Park, Stellenbosch, 7600')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (13, 'Client Service Champion', 'Assist clients in-branch with their banking needs.', 'Matric. Passion for client service.', 'R180,000 - R240,000 PA', 'Stellenbosch, Western Cape', 'Full-time', 'On-site')""")

        # 14. Vodacom
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Vodacom', 'Telecommunications', 'Leading African mobile communications company.', 'https.www.vodacom.com', 'Vodacom Corporate Park, 082 Vodacom Blvd, Midrand, 1685')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (14, 'IoT Solutions Developer', 'Develop and support IoT solutions for enterprise clients.', 'BEng/BSc Computer Science. 3+ years Java/Python.', 'R600,000 - R800,000 PA', 'Midrand, Gauteng', 'Full-time', 'Hybrid')""")

        # 15. Allan Gray
        cur.execute("""INSERT INTO businesses (name, industry, description, website, address) VALUES ('Allan Gray', 'Investment Management', 'Africa''s largest privately owned investment manager.', 'https.www.allangray.co.za', '1 Silo Square, V&A Waterfront, Cape Town, 8001')""")
        cur.execute("""INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, employment_type, work_arrangement) VALUES (15, 'Investment Analyst', 'Conduct deep fundamental research on JSE-listed companies.', 'BCom (Hons) / CFA Charterholder. Passion for investing.', 'R750,000 - R1,100,000 PA', 'Cape Town, Western Cape', 'Full-time', 'On-site')""")
        
        conn.commit()
    except Exception as e:
        print(f"An error occurred during data population: {e}")
        conn.rollback()


# ----------------------------------------------------------------------
#  All other functions (userExists, getUsersDetails, getUserById, etc.)
# ----------------------------------------------------------------------

def userExists(conn: sqlite3.Connection, username: str, email: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE username = ? OR email = ?", (username, email))
    return cur.fetchone() is not None
    
def emailExists(conn: sqlite3.Connection, email: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    return cur.fetchone() is not None

def getUsersDetails(conn: sqlite3.Connection, uore: str) -> Optional[Dict[str, Any]]:
    # ... (unchanged) ...
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

def getUserById(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    # ... (unchanged) ...
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

def updateUserProfile(conn: sqlite3.Connection, profile_data: Dict[str, Any]) -> bool:
    # ... (unchanged) ...
    cur = conn.cursor()
    fields: list[str] = []
    values: list[Any] = []
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

# ... (CV functions are unchanged) ...
def _getUserCVs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("SELECT cv_id, user_id, cv_name, file_path, file_size, mime_type, is_primary, uploaded_at FROM cvs WHERE user_id = ? ORDER BY uploaded_at DESC", (user_id,))
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        d = dict(zip(columns, row))
        result.append({"cvId": d["cv_id"], "userId": d["user_id"], "cvName": d["cv_name"], "filePath": d["file_path"], "fileSize": d.get("file_size"), "mimeType": d.get("mime_type"), "isPrimary": bool(d["is_primary"]), "uploadedAt": d["uploaded_at"]})
    return result
def getUserCVs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    return _getUserCVs(conn, user_id)
def addCV(conn: sqlite3.Connection, cv_data: Dict[str, Any]) -> Optional[int]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("INSERT INTO cvs (user_id, cv_name, file_path, file_size, mime_type, is_primary, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (cv_data["userId"], cv_data["cvName"], cv_data["filePath"], cv_data.get("fileSize"), cv_data.get("mimeType"), cv_data.get("isPrimary", False), cv_data.get("uploadedAt", datetime.now(timezone.utc).isoformat()),))
    conn.commit()
    return cur.lastrowid
def deleteCV(conn: sqlite3.Connection, cv_id: int, user_id: int) -> bool:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("DELETE FROM cvs WHERE cv_id = ? AND user_id = ?", (cv_id, user_id))
    conn.commit()
    return cur.rowcount > 0
def setPrimaryCV(conn: sqlite3.Connection, cv_id: int, user_id: int) -> bool:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("UPDATE cvs SET is_primary = 0 WHERE user_id = ?", (user_id,))
    cur.execute("UPDATE cvs SET is_primary = 1 WHERE cv_id = ? AND user_id = ?", (cv_id, user_id))
    conn.commit()
    return cur.rowcount > 0

# ... (Qualifications functions are unchanged) ...
def _getUserQualifications(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("SELECT qualification_id, user_id, qualification_type, institution, field_of_study, qualification_name, start_date, end_date, is_current, grade_or_gpa, description, created_at FROM qualifications WHERE user_id = ? ORDER BY end_date DESC NULLS LAST, start_date DESC", (user_id,))
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        d = dict(zip(columns, row))
        result.append({"qualificationId": d["qualification_id"], "userId": d["user_id"], "qualificationType": d["qualification_type"], "institution": d["institution"], "fieldOfStudy": d.get("field_of_study"), "qualificationName": d["qualification_name"], "startDate": d.get("start_date"), "endDate": d.get("end_date"), "isCurrent": bool(d["is_current"]), "gradeOrGpa": d.get("grade_or_gpa"), "description": d.get("description"), "createdAt": d["created_at"]})
    return result
def getUserQualifications(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    return _getUserQualifications(conn, user_id)
def addQualification(conn: sqlite3.Connection, qual_data: Dict[str, Any]) -> Optional[int]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("INSERT INTO qualifications (user_id, qualification_type, institution, field_of_study, qualification_name, start_date, end_date, is_current, grade_or_gpa, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (qual_data["userId"], qual_data["qualificationType"], qual_data["institution"], qual_data.get("fieldOfStudy"), qual_data["qualificationName"], qual_data.get("startDate"), qual_data.get("endDate"), int(qual_data.get("isCurrent", False)), qual_data.get("gradeOrGpa"), qual_data.get("description"), qual_data.get("createdAt", datetime.now(timezone.utc).isoformat()),))
    conn.commit()
    return cur.lastrowid
def updateQualification(conn: sqlite3.Connection, qualification_id: int, user_id: int, qual_data: Dict[str, Any]) -> bool:
    # ... (unchanged) ...
    cur = conn.cursor()
    fields: list[str] = []
    values: list[Any] = []
    field_map = {"qualificationType": "qualification_type", "institution": "institution", "fieldOfStudy": "field_of_study", "qualificationName": "qualification_name", "startDate": "start_date", "endDate": "end_date", "isCurrent": "is_current", "gradeOrGpa": "grade_or_gpa", "description": "description"}
    for api, db in field_map.items():
        if api in qual_data:
            fields.append(f"{db} = ?")
            if api == "isCurrent": values.append(int(qual_data[api]))
            else: values.append(qual_data[api])
    if not fields: return False
    values.extend([qualification_id, user_id])
    query = f"UPDATE qualifications SET {', '.join(fields)} WHERE qualification_id = ? AND user_id = ?"
    cur.execute(query, tuple(values))
    conn.commit()
    return cur.rowcount > 0
def deleteQualification(conn: sqlite3.Connection, qualification_id: int, user_id: int) -> bool:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("DELETE FROM qualifications WHERE qualification_id = ? AND user_id = ?", (qualification_id, user_id))
    conn.commit()
    return cur.rowcount > 0

# ... (Stats & Saved Jobs functions are unchanged) ...
def getUserApplicationsCount(conn: sqlite3.Connection, user_id: int) -> int:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM job_applications WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 0
def getUserSavedJobsCount(conn: sqlite3.Connection, user_id: int) -> int:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM saved_jobs WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 0
def _getSavedJobs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("SELECT saved_job_id, user_id, job_title, company_name, job_location, salary_range, job_description, saved_at FROM saved_jobs WHERE user_id = ? ORDER BY saved_at DESC", (user_id,))
    columns: List[str] = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        d: Dict[str, Any] = dict(zip(columns, row))
        result.append({"savedJobId": d["saved_job_id"], "userId": d["user_id"], "jobTitle": d["job_title"], "companyName": d["company_name"], "jobLocation": d.get("job_location"), "salaryRange": d.get("salary_range"), "jobDescription": d.get("job_description"), "savedAt": d["saved_at"]})
    return result
def getSavedJobs(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    return _getSavedJobs(conn, user_id)
def addSavedJob(conn: sqlite3.Connection, job_data: Dict[str, Any]) -> Optional[int]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("INSERT INTO saved_jobs (user_id, job_title, company_name, job_location, salary_range, job_description, saved_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (job_data["userId"], job_data["jobTitle"], job_data["companyName"], job_data.get("jobLocation"), job_data.get("salaryRange"), job_data.get("jobDescription"), job_data.get("savedAt", datetime.now(timezone.utc).isoformat()),))
    conn.commit()
    return cur.lastrowid
def deleteSavedJob(conn: sqlite3.Connection, saved_job_id: int, user_id: int) -> bool:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("DELETE FROM saved_jobs WHERE saved_job_id = ? AND user_id = ?", (saved_job_id, user_id))
    conn.commit()
    return cur.rowcount > 0

# ... (Business & Job Listing functions are unchanged) ...
def addBusiness(conn: sqlite3.Connection, biz_data: Dict[str, Any]) -> Optional[int]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("INSERT INTO businesses (name, industry, description, website, address, created_at) VALUES (?, ?, ?, ?, ?, ?)", (biz_data["name"], biz_data.get("industry"), biz_data.get("description"), biz_data.get("website"), biz_data.get("address"), biz_data.get("createdAt", datetime.now(timezone.utc).isoformat()),))
    conn.commit()
    return cur.lastrowid
def addJob(conn: sqlite3.Connection, job_data: Dict[str, Any]) -> Optional[int]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("INSERT INTO jobs (business_id, job_title, description, requirements, salary_range, location, work_arrangement, employment_type, date_posted, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (job_data["businessId"], job_data["jobTitle"], job_data["description"], job_data.get("requirements"), job_data.get("salaryRange"), job_data.get("location"), job_data.get("workArrangement"), job_data.get("employmentType"), job_data.get("datePosted", datetime.now(timezone.utc).isoformat()), int(job_data.get("isActive", True)),))
    conn.commit()
    return cur.lastrowid
def getActiveJobs(conn: sqlite3.Connection, limit: int, offset: int) -> List[Dict[str, Any]]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("SELECT j.job_id, j.job_title, j.description, j.requirements, j.salary_range, j.location, j.work_arrangement, j.employment_type, j.date_posted, j.business_id, b.name AS business_name, b.address AS business_address, b.website AS business_website FROM jobs j JOIN businesses b ON j.business_id = b.business_id WHERE j.is_active = 1 ORDER BY j.date_posted DESC LIMIT ? OFFSET ?", (limit, offset))
    columns: List[str] = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        d: Dict[str, Any] = dict(zip(columns, row))
        result.append({"jobId": d["job_id"], "jobTitle": d["job_title"], "description": d["description"], "requirements": d.get("requirements"), "salaryRange": d.get("salary_range"), "location": d.get("location"), "workArrangement": d.get("work_arrangement"), "employmentType": d.get("employment_type"), "datePosted": d["date_posted"], "businessId": d["business_id"], "businessName": d.get("business_name"), "businessAddress": d.get("business_address"), "businessWebsite": d.get("business_website")})
    return result
def getJobById(conn: sqlite3.Connection, job_id: int) -> Optional[Dict[str, Any]]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("SELECT j.job_id, j.job_title, j.description, j.requirements, j.salary_range, j.location, j.work_arrangement, j.employment_type, j.date_posted, j.business_id, j.is_active, b.name AS business_name, b.address AS business_address, b.website AS business_website, b.industry AS business_industry, b.description AS business_description FROM jobs j JOIN businesses b ON j.business_id = b.business_id WHERE j.job_id = ?", (job_id,))
    row = cur.fetchone()
    if not row: return None
    d: Dict[str, Any] = dict(row)
    return {"jobId": d["job_id"], "jobTitle": d["job_title"], "description": d["description"], "requirements": d.get("requirements"), "salaryRange": d.get("salary_range"), "location": d.get("location"), "workArrangement": d.get("work_arrangement"), "employmentType": d.get("employment_type"), "datePosted": d["date_posted"], "isActive": bool(d["is_active"]), "businessId": d["business_id"], "businessName": d.get("business_name"), "businessAddress": d.get("business_address"), "businessWebsite": d.get("business_website"), "businessIndustry": d.get("business_industry"), "businessDescription": d.get("business_description")}
def searchJobs(conn: sqlite3.Connection, query: Optional[str] = None, employment_type: Optional[str] = None, work_arrangement: Optional[str] = None, location: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    # ... (unchanged) ...
    cur = conn.cursor()
    base_query = "SELECT j.job_id, j.job_title, j.description, j.requirements, j.salary_range, j.location, j.work_arrangement, j.employment_type, j.date_posted, j.business_id, b.name AS business_name, b.address AS business_address, b.website AS business_website FROM jobs j JOIN businesses b ON j.business_id = b.business_id WHERE j.is_active = 1"
    params: List[Any] = []
    if query:
        search_term = f"%{query.lower()}%"
        base_query += " AND (LOWER(j.job_title) LIKE ? OR LOWER(j.description) LIKE ? OR LOWER(j.requirements) LIKE ? OR LOWER(j.location) LIKE ? OR LOWER(b.name) LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term, search_term])
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
    columns: List[str] = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        d: Dict[str, Any] = dict(zip(columns, row))
        result.append({"jobId": d["job_id"], "jobTitle": d["job_title"], "description": d["description"], "requirements": d.get("requirements"), "salaryRange": d.get("salary_range"), "location": d.get("location"), "workArrangement": d.get("work_arrangement"), "employmentType": d.get("employment_type"), "datePosted": d["date_posted"], "businessId": d["business_id"], "businessName": d.get("business_name"), "businessAddress": d.get("business_address"), "businessWebsite": d.get("business_website")})
    return result

# ... (Union functions are unchanged) ...
def unionExists(conn: sqlite3.Connection, register_num: str) -> bool:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM unions WHERE register_num = ?", (register_num,))
    return cur.fetchone() is not None
def getUnions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("SELECT * FROM unions")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]
def createUnion(conn: sqlite3.Connection, union_data: Dict[str, Any]) -> bool:
    # ... (unchanged) ...
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO unions (register_num, sector_info, membership_size, is_active_council, created_at) VALUES (?, ?, ?, ?, ?)", (union_data["register_num"], union_data["sector_info"], union_data.get("membership_size", 0), int(union_data.get("is_active_council", False)), union_data.get("createdAt", datetime.now(timezone.utc).isoformat()),))
        conn.commit()
        return True
    except sqlite3.IntegrityError: return False
    except Exception as e: print(f"Error creating union: {e}"); conn.rollback(); return False
def workerInUnion(conn: sqlite3.Connection, worker_id: int, union_id: int) -> bool:
    # ... (unchanged) ...
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM union_members WHERE worker_id = ? AND union_id = ?", (worker_id, union_id))
    return cur.fetchone() is not None
def getUnionMembers(conn: sqlite3.Connection, union_id: Optional[int] = None) -> List[Dict[str, Any]]:
    # ... (unchanged) ...
    cur = conn.cursor()
    if union_id: cur.execute("SELECT * FROM union_members WHERE union_id = ?", (union_id,))
    else: cur.execute("SELECT * FROM union_members")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]
def addUnionMember(conn: sqlite3.Connection, member_data: Dict[str, Any]) -> Optional[int]:
    # ... (unchanged) ...
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO union_members (worker_id, union_id, membership_num, status, created_at) VALUES (?, ?, ?, ?, ?)", (member_data["worker_id"], member_data["union_id"], member_data["membership_num"], member_data.get("status", "active"), member_data.get("createdAt", datetime.now(timezone.utc).isoformat()),))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError: return None
    except Exception as e: print(f"Error adding union member: {e}"); conn.rollback(); return None

# --- 4. ADD NEW PASSWORD RESET FUNCTIONS ---
def create_reset_code(conn: sqlite3.Connection, email: str) -> str:
    """Generates a 6-digit code, stores it, and returns it."""
    # Invalidate old codes
    cur = conn.cursor()
    cur.execute("UPDATE password_reset_codes SET is_used = 1 WHERE email = ?", (email,))
    
    # Generate new code
    code = "".join(random.choices(string.digits, k=6))
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    
    cur.execute(
        """INSERT INTO password_reset_codes (email, code, expires_at)
           VALUES (?, ?, ?)""",
        (email, code, expires_at)
    )
    conn.commit()
    print(f"Generated reset code {code} for {email}")
    # In a real app, you would email this code instead of printing it
    return code

def verify_reset_code(conn: sqlite3.Connection, email: str, code: str) -> bool:
    """Checks if a code is valid, unused, and not expired."""
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cur.execute(
        """SELECT 1 FROM password_reset_codes
           WHERE email = ? AND code = ? AND is_used = 0 AND expires_at > ?""",
        (email, code, now)
    )
    return cur.fetchone() is not None

def reset_user_password(conn: sqlite3.Connection, email: str, code: str, new_password_hash: str) -> bool:
    """Resets the password if the code is valid, then invalidates the code."""
    if not verify_reset_code(conn, email, code):
        print(f"Invalid code {code} for {email} used in reset attempt")
        return False
        
    cur = conn.cursor()
    # Update the user's password
    cur.execute("UPDATE users SET password_hash = ? WHERE email = ?", (new_password_hash, email))
    if cur.rowcount == 0:
        return False # User not found
    
    # Invalidate the used code
    cur.execute(
        "UPDATE password_reset_codes SET is_used = 1 WHERE email = ? AND code = ?",
        (email, code)
    )
    conn.commit()
    return True
