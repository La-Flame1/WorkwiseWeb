import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime

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

    cur.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            worker_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            phone TEXT,
            bio TEXT,
            experience_years INTEGER DEFAULT 0,
            availability_status TEXT DEFAULT 'available',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS governments (
        government_id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_name TEXT UNIQUE NOT NULL,
        contact_info TEXT NOT NULL,
        regulatory_focus TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS government_programs (
        program_id INTEGER PRIMARY KEY AUTOINCREMENT,
        government_id INTEGER NOT NULL,
        program_name TEXT NOT NULL,
        eligibility_criteria TEXT NOT NULL,
        skills_focus TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (government_id) REFERENCES governments (government_id) ON DELETE CASCADE
    )
''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS training_institutions (
        institution_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        location TEXT NOT NULL,
        contact_info TEXT NOT NULL,
        accreditation_status TEXT DEFAULT 'pending',
        is_active BOOLEAN DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )
''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_government_programs_gov ON government_programs (government_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_training_institutions_name ON training_institutions (name)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_jobs_employer ON jobs (employer_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_applications_worker ON applications (worker_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_applications_job ON applications (job_id)')

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

def createWorker(conn: sqlite3.Connection, worker_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO workers (user_id, phone, bio, experience_years, availability_status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (worker_data['user_id'], worker_data.get('phone'), worker_data.get('bio'),
          worker_data.get('experience_years', 0), worker_data.get('availability_status', 'available'),
          datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    return cur.lastrowid

def getWorkers(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM workers")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def createEmployer(conn: sqlite3.Connection, employer_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO employers (user_id, company_name, location, industry, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (employer_data['user_id'], employer_data['company_name'], employer_data.get('location'),
          employer_data.get('industry'), datetime.now().isoformat()))
    conn.commit()
    return cur.lastrowid

def getEmployers(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM employers")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def createJob(conn: sqlite3.Connection, job_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO jobs (employer_id, title, description, salary_range, required_skills, compliance_required, deadline, posted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (job_data['employer_id'], job_data['title'], job_data['description'],
          job_data.get('salary_range'), job_data.get('required_skills'), job_data.get('compliance_required', False),
          job_data.get('deadline'), datetime.now().isoformat()))
    conn.commit()
    return cur.lastrowid

def getJobs(conn: sqlite3.Connection, employer_id: Optional[int] = None) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    if employer_id:
        cur.execute("SELECT * FROM jobs WHERE employer_id = ?", (employer_id,))
    else:
        cur.execute("SELECT * FROM jobs")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def createApplication(conn: sqlite3.Connection, app_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applications (job_id, worker_id, cover_letter, applied_at)
        VALUES (?, ?, ?, ?)
    """, (app_data['job_id'], app_data['worker_id'], app_data.get('cover_letter'),
          datetime.now().isoformat()))
    conn.commit()
    return cur.lastrowid

def getApplications(conn: sqlite3.Connection, worker_id: Optional[int] = None, job_id: Optional[int] = None) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    if worker_id:
        cur.execute("SELECT * FROM applications WHERE worker_id = ?", (worker_id,))
    elif job_id:
        cur.execute("SELECT * FROM applications WHERE job_id = ?", (job_id,))
    else:
        cur.execute("SELECT * FROM applications")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def createCourse(conn: sqlite3.Connection, course_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO courses (title, description, provider, duration_hours, cost, skills_covered, certification_available, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (course_data['title'], course_data['description'], course_data.get('provider'),
          course_data.get('duration_hours', 0), course_data.get('cost', 0.0), course_data.get('skills_covered'),
          course_data.get('certification_available', False), datetime.now().isoformat()))
    conn.commit()
    return cur.lastrowid

def getCourses(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM courses")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def enrollWorkerInCourse(conn: sqlite3.Connection, enrollment_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO worker_courses (worker_id, course_id, enrollment_date)
        VALUES (?, ?, ?)
    """, (enrollment_data['worker_id'], enrollment_data['course_id'], datetime.now().isoformat()))
    conn.commit()
    return cur.lastrowid

def getWorkerCourses(conn: sqlite3.Connection, worker_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM worker_courses WHERE worker_id = ?", (worker_id,))
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

def governmentExists(conn: sqlite3.Connection, department_name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM governments WHERE department_name = ?", (department_name,))
    return cur.fetchone() is not None

def createGovernment(conn: sqlite3.Connection, gov_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO governments (department_name, contact_info, regulatory_focus, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (gov_data['department_name'], gov_data['contact_info'], gov_data['regulatory_focus'],
          datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    return cur.lastrowid

def getGovernments(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM governments")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

# New functions for government_programs
def createGovernmentProgram(conn: sqlite3.Connection, program_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO government_programs (government_id, program_name, eligibility_criteria, skills_focus, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (program_data['government_id'], program_data['program_name'], program_data['eligibility_criteria'],
          program_data['skills_focus'], program_data.get('is_active', 1), datetime.now().isoformat()))
    conn.commit()
    return cur.lastrowid

def getGovernmentPrograms(conn: sqlite3.Connection, government_id: Optional[int] = None) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    if government_id:
        cur.execute("SELECT * FROM government_programs WHERE government_id = ?", (government_id,))
    else:
        cur.execute("SELECT * FROM government_programs")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]

# New functions for training_institutions
def trainingInstitutionExists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM training_institutions WHERE name = ?", (name,))
    return cur.fetchone() is not None

def createTrainingInstitution(conn: sqlite3.Connection, inst_data: Dict[str, Any]) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO training_institutions (name, location, contact_info, accreditation_status, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (inst_data['name'], inst_data['location'], inst_data['contact_info'],
          inst_data.get('accreditation_status', 'pending'), inst_data.get('is_active', 1), datetime.now().isoformat()))
    conn.commit()
    return cur.lastrowid

def getTrainingInstitutions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM training_institutions")
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]