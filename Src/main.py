import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security.api_key import APIKeyHeader
from fastapi.exception_handlers import http_exception_handler as defaultHttpHandler
from passlib.context import CryptContext
from Models.models import RegisterIn, RegisterOut, LoginIn, LoginOut, TrainingInstitutionIn, TrainingInstitutionOut, UnionIn, UnionOut, UnionMemberIn, UnionMemberOut, WorkerIn, WorkerOut, EmployerIn, EmployerOut, JobIn, JobOut, ApplicationIn, ApplicationOut, CourseIn, CourseOut, WorkerCourseIn, WorkerCourseOut, GovernmentIn, GovernmentOut, GovernmentProgramIn, GovernmentProgramOut

from Database.db import getTrainingInstitutions, initDatabase, getDatabase, trainingInstitutionExists, userExists, getUsersDetails, unionExists, getUnions, workerInUnion, getUnionMembers, createWorker as dbCreateWorker, getWorkers, createEmployer, getEmployers, createJob as dbCreateJob, getJobs, createApplication as dbCreateApplication, getApplications, getCourses, getWorkerCourses, enrollWorkerInCourse as dbEnrollWorkerInCourse, createCourse as dbCreateCourse, governmentExists, createGovernment as dbCreateGovernment, getGovernments, createGovernmentProgram as dbCreateGovernmentProgram, getGovernmentPrograms, createTrainingInstitution as dbCreateTrainingInstitution

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    initDatabase()
    yield
    # Shutdown (if needed in the future)

app = FastAPI(
    title="Workwise API",
    version="1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "auth", "description": "Authentication endpoints"},
        {"name": "unions", "description": "Union management"},
        {"name": "union_members", "description": "Union membership management"},
        {"name": "workers", "description": "Worker profiles management"},
        {"name": "employers", "description": "Employer profiles management"},
        {"name": "jobs", "description": "Job postings management"},
        {"name": "applications", "description": "Job applications management"},
        {"name": "courses", "description": "Skills courses management"},
        {"name": "worker_courses", "description": "Worker course enrollments management"},
        {"name": "governments", "description": "Government departments management"},
        {"name": "government_programs", "description": "Government programs management"},
        {"name": "training_institutions", "description": "Training institutions management"},
        {"name": "geolocation", "description": "Free geocoding and mapping utilities (OSM-based)"}
    ],
    swagger_ui_default_parameters=[{"name": "X-Endpoint-Token", "in": "header", "required": True}]
)
templates = Jinja2Templates(directory="Templates")

endpoint_token = APIKeyHeader(name="X-Endpoint-Token")

# Load individual tokens from .env and build dict
endpointTokens = {
    "POST:/v1/workwise/account": os.getenv("TOKEN_POST_ACCOUNT"),
    "POST:/v1/workwise/user": os.getenv("TOKEN_POST_USER"),
    "GET:/v1/workwise/unions": os.getenv("TOKEN_GET_UNIONS"),
    "POST:/v1/workwise/unions": os.getenv("TOKEN_POST_UNIONS"),
    "GET:/v1/workwise/union_members": os.getenv("TOKEN_GET_UNION_MEMBERS"),
    "POST:/v1/workwise/union_members": os.getenv("TOKEN_POST_UNION_MEMBERS"),
    "POST:/v1/workwise/workers": os.getenv("TOKEN_POST_WORKERS"),
    "GET:/v1/workwise/workers": os.getenv("TOKEN_GET_WORKERS"),
    "POST:/v1/workwise/employers": os.getenv("TOKEN_POST_EMPLOYERS"),
    "GET:/v1/workwise/employers": os.getenv("TOKEN_GET_EMPLOYERS"),
    "POST:/v1/workwise/jobs": os.getenv("TOKEN_POST_JOBS"),
    "GET:/v1/workwise/jobs": os.getenv("TOKEN_GET_JOBS"),
    "POST:/v1/workwise/applications": os.getenv("TOKEN_POST_APPLICATIONS"),
    "GET:/v1/workwise/applications": os.getenv("TOKEN_GET_APPLICATIONS"),
    "POST:/v1/workwise/courses": os.getenv("TOKEN_POST_COURSES"),
    "GET:/v1/workwise/courses": os.getenv("TOKEN_GET_COURSES"),
    "POST:/v1/workwise/worker_courses": os.getenv("TOKEN_POST_WORKER_COURSES"),
    "GET:/v1/workwise/worker_courses": os.getenv("TOKEN_GET_WORKER_COURSES"),
    "POST:/v1/workwise/governments": os.getenv("TOKEN_POST_GOVERNMENTS"),
    "GET:/v1/workwise/governments": os.getenv("TOKEN_GET_GOVERNMENTS"),
    "POST:/v1/workwise/government_programs": os.getenv("TOKEN_POST_GOVERNMENT_PROGRAMS"),
    "GET:/v1/workwise/government_programs": os.getenv("TOKEN_GET_GOVERNMENT_PROGRAMS"),
    "POST:/v1/workwise/training_institutions": os.getenv("TOKEN_POST_TRAINING_INSTITUTIONS"),
    "GET:/v1/workwise/training_institutions": os.getenv("TOKEN_GET_TRAINING_INSTITUTIONS"),
}

# Validate all tokens are loaded (required; raises if missing)
missing = [k for k, v in endpointTokens.items() if not v]
if missing:
    raise ValueError(f"Missing tokens in .env: {missing}")

# Helper to safely get token (type-safe after validation)
def getToken(method: str, path: str) -> str:
    token = endpointTokens.get(key(method, path))
    if not token:
        raise ValueError(f"Token not found for {method}:{path}")
    return token

# uvicorn main:app --reload --host 0.0.0.0 --port 8000

def key(method: str, path: str) -> str:
    return f"{method.upper()}:{path}"

def requireEndpointToken(expected_token: str):
    def dependency(token: str = Depends(endpoint_token)):
        if token != expected_token:
            raise HTTPException(status_code=401, detail="Missing or invalid endpoint token")
        return True
    return dependency

pwd = CryptContext(schemes=["argon2"], deprecated="auto")

@app.exception_handler(HTTPException)
async def customHttpExceptionHandler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        accepts_html = "text/html" in request.headers.get("accept", "").lower()
        if accepts_html:
            return templates.TemplateResponse("401.html", {"request": request}, status_code=401)
        return JSONResponse({"detail": exc.detail or "Unauthorized"}, status_code=401)
    return await defaultHttpHandler(request, exc)

@app.get("/v1/ping")
def ping() -> dict[str, Any]:
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}

@app.post(
    "/v1/workwise/account",
    response_model=RegisterOut,
    tags=["auth"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/account")))]
)
def register(body: RegisterIn):
    conn = getDatabase()
    try:
        if userExists(conn, body.username, body.email):
            raise HTTPException(status_code=409, detail="Username or email already exists")

        hashed = pwd.hash(body.password)
        created_at = datetime.now(timezone.utc).isoformat()

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, email, password_hash, role, created_at, is_active)
            VALUES (?, ?, ?, 'user', ?, 1)
        """, (body.username, body.email, hashed, created_at))
        conn.commit()

        user_id = cur.lastrowid
        if user_id is None:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        return RegisterOut(
            userId=user_id,
            username=body.username,
            email=body.email,
            role="user",
            createdAt=created_at,
            isActive=True
        )
    finally:
        conn.close()

@app.get("/v1/workwise/account", tags=["auth"])
def registerProbeHtml():
    raise HTTPException(status_code=401, detail="Missing or invalid endpoint token")

@app.post(
    "/v1/workwise/user",
    response_model=LoginOut,
    tags=["auth"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/user")))]
)
def login(body: LoginIn):
    conn = getDatabase()
    try:
        row = getUsersDetails(conn, body.usernameOrEmail)
        if not row or not pwd.verify(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return LoginOut(
            userId=row["user_id"],
            username=row["username"],
            email=row["email"],
            role=row["role"]
        )
    finally:
        conn.close()

@app.get("/v1/workwise/user", tags=["auth"])
def loginProbeHtml() -> None:
    raise HTTPException(status_code=401, detail="Missing or invalid endpoint token")

# New routes for Unions (tagged "unions")
@app.get(
    "/v1/workwise/unions",
    response_model=List[UnionOut],
    tags=["unions"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/unions")))]
)
def listUnions():
    conn = getDatabase()
    try:
        unions = getUnions(conn)  # Returns list of dicts with union fields
        return [UnionOut(**union) for union in unions]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/unions",
    response_model=UnionOut,
    tags=["unions"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/unions")))]
)
def createUnion(body: UnionIn):
    conn = getDatabase()
    try:
        if unionExists(conn, body.register_num):
            raise HTTPException(status_code=409, detail="Union registration number already exists")

        created_at = datetime.now(timezone.utc).isoformat()

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO unions (register_num, sector_info, membership_size, is_active_council, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (body.register_num, body.sector_info, body.membership_size, body.is_active_council, created_at))
        conn.commit()

        union_id = cur.lastrowid
        if union_id is None:
            raise HTTPException(status_code=500, detail="Failed to create union")
        
        return UnionOut(
            unionId=union_id,
            register_num=body.register_num,
            sector_info=body.sector_info,
            membership_size=body.membership_size,
            is_active_council=body.is_active_council,
            createdAt=created_at
        )
    finally:
        conn.close()

# New routes for Union Members (tagged "union_members")
@app.get(
    "/v1/workwise/union_members",
    response_model=List[UnionMemberOut],
    tags=["union_members"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/union_members")))]
)
def listUnionMembers(union_id: Optional[int] = None):
    conn = getDatabase()
    try:
        members = getUnionMembers(conn, union_id)  # If union_id provided, filter by union; else all
        return [UnionMemberOut(**member) for member in members]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/union_members",
    response_model=UnionMemberOut,
    tags=["union_members"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/union_members")))]
)
def addUnionMember(body: UnionMemberIn):
    conn = getDatabase()
    try:
        if workerInUnion(conn, body.worker_id, body.union_id):
            raise HTTPException(status_code=409, detail="Worker is already a member of this union")

        # Generate membership_num if not provided (e.g., auto-increment or UUID)
        membership_num = body.membership_num or f"MEM-{body.worker_id}-{body.union_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO union_members (worker_id, union_id, membership_num, status)
            VALUES (?, ?, ?, ?)
        """, (body.worker_id, body.union_id, membership_num, body.status or "active"))
        conn.commit()

        membership_id = cur.lastrowid
        if membership_id is None:
            raise HTTPException(status_code=500, detail="Failed to add union member")
        
        # Update union's membership_size
        cur.execute("UPDATE unions SET membership_size = membership_size + 1 WHERE union_id = ?", (body.union_id,))
        conn.commit()
        
        return UnionMemberOut(
            membership_id=membership_id, # type: ignore
            worker_id=body.worker_id,
            union_id=body.union_id,
            membership_num=membership_num,
            status=body.status or "active"
        )
    finally:
        conn.close()
# Workers (tagged "workers")
@app.post(
    "/v1/workwise/workers",
    response_model=WorkerOut,
    tags=["workers"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/workers")))]
)
def createWorker(body: WorkerIn, current_user_id: int = 1):  # Assume from auth; replace with Depends(get_current_user)
    conn = getDatabase()
    try:
        worker_data: dict[str, Any] = {"user_id": current_user_id, **body.model_dump()}
        worker_id: Optional[int] = dbCreateWorker(conn, worker_data)
        if worker_id is None:
            raise HTTPException(status_code=500, detail="Failed to create worker")
        
        created_at = datetime.now(timezone.utc).isoformat()
        return WorkerOut(
            workerId=worker_id,
            userId=current_user_id,
            createdAt=created_at,
            updatedAt=created_at,
            **body.model_dump()
        )
    finally:
        conn.close()

@app.get(
    "/v1/workwise/workers",
    response_model=List[WorkerOut],
    tags=["workers"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/workers")))]
)
def listWorkers():
    conn = getDatabase()
    try:
        workers = getWorkers(conn)
        created_at = datetime.now(timezone.utc).isoformat()  # For uniformity
        return [WorkerOut(
            workerId=w["worker_id"],
            userId=w["user_id"],
            createdAt=w["created_at"] or created_at,
            updatedAt=w["updated_at"] or created_at,
            **{k: v for k, v in w.items() if k not in ["worker_id", "user_id", "created_at", "updated_at"]}
        ) for w in workers]
    finally:
        conn.close()

# Employers (tagged "employers")
@app.post(
    "/v1/workwise/employers",
    response_model=EmployerOut,
    tags=["employers"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/employers")))]
)
def createEmployerEndpoint(body: EmployerIn, current_user_id: int = 1):
    conn = getDatabase()
    try:
        row = getUsersDetails(conn, body.company_name or "")  # Adjust
        if not row or row["role"] != "employer":
            raise HTTPException(status_code=400, detail="User must exist with 'employer' role")

        employer_data: dict[str, Any] = {"user_id": current_user_id, **body.model_dump()}
        employer_id: Optional[int] = createEmployer(conn, employer_data)
        if employer_id is None:
            raise HTTPException(status_code=500, detail="Failed to create employer")
        
        created_at = datetime.now(timezone.utc).isoformat()
        return EmployerOut(
            employerId=employer_id,
            userId=current_user_id,
            createdAt=created_at,
            **body.model_dump()
        )
    finally:
        conn.close()

@app.get(
    "/v1/workwise/employers",
    response_model=List[EmployerOut],
    tags=["employers"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/employers")))]
)
def listEmployers():
    conn = getDatabase()
    try:
        employers = getEmployers(conn)
        created_at = datetime.now(timezone.utc).isoformat()
        return [EmployerOut(
            employerId=e["employer_id"],
            userId=e["user_id"],
            createdAt=e["created_at"] or created_at,
            **{k: v for k, v in e.items() if k not in ["employer_id", "user_id", "created_at"]}
        ) for e in employers]
    finally:
        conn.close()

# Jobs (tagged "jobs")
@app.post(
    "/v1/workwise/jobs",
    response_model=JobOut,
    tags=["jobs"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/jobs")))]
)
def createJob(body: JobIn, current_employer_id: int = 1):
    conn = getDatabase()
    try:
        posted_at = datetime.now(timezone.utc).isoformat()
        job_data: dict[str, Any] = {"employer_id": current_employer_id, **body.model_dump(), "posted_at": posted_at}
        job_id: Optional[int] = dbCreateJob(conn, job_data)
        if job_id is None:
            raise HTTPException(status_code=500, detail="Failed to create job")
        
        return JobOut(
            jobId=job_id,
            employerId=current_employer_id,
            postedAt=posted_at,
            **body.model_dump()
        )
    finally:
        conn.close()

@app.get(
    "/v1/workwise/jobs",
    response_model=List[JobOut],
    tags=["jobs"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/jobs")))]
)
def listJobs(employer_id: Optional[int] = None):
    conn = getDatabase()
    try:
        jobs = getJobs(conn, employer_id)
        posted_at = datetime.now(timezone.utc).isoformat()
        return [JobOut(
            jobId=j["job_id"],
            employerId=j["employer_id"],
            postedAt=j["posted_at"] or posted_at,
            **{k: v for k, v in j.items() if k not in ["job_id", "employer_id", "posted_at"]}
        ) for j in jobs]
    finally:
        conn.close()

# Applications (tagged "applications")
@app.post(
    "/v1/workwise/applications",
    response_model=ApplicationOut,
    tags=["applications"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/applications")))]
)
def createApplication(body: ApplicationIn, current_worker_id: int = 1):
    conn = getDatabase()
    try:
        applied_at = datetime.now(timezone.utc).isoformat()
        app_data: dict[str, Any] = {"job_id": body.job_id, "worker_id": current_worker_id, **body.model_dump(), "applied_at": applied_at}
        app_id: Optional[int] = dbCreateApplication(conn, app_data)
        if app_id is None:
            raise HTTPException(status_code=500, detail="Failed to create application")
        
        return ApplicationOut(
            applicationId=app_id,
            workerId=current_worker_id,
            appliedAt=applied_at,
            matchScore=0.0,  # Compute later
            **body.model_dump()
        )
    finally:
        conn.close()

@app.get(
    "/v1/workwise/applications",
    response_model=List[ApplicationOut],
    tags=["applications"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/applications")))]
)
def listApplications(worker_id: Optional[int] = None, job_id: Optional[int] = None):
    conn = getDatabase()
    try:
        apps = getApplications(conn, worker_id, job_id)
        applied_at = datetime.now(timezone.utc).isoformat()
        return [ApplicationOut(
            applicationId=a["application_id"],
            workerId=a["worker_id"],
            appliedAt=a["applied_at"] or applied_at,
            matchScore=a["match_score"] or 0.0,
            **{k: v for k, v in a.items() if k not in ["application_id", "worker_id", "applied_at", "match_score"]}
        ) for a in apps]
    finally:
        conn.close()

# Courses (tagged "courses")
@app.post(
    "/v1/workwise/courses",
    response_model=CourseOut,
    tags=["courses"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/courses")))]
)
def createCourse(body: CourseIn):
    conn = getDatabase()
    try:
        created_at = datetime.now(timezone.utc).isoformat()
        course_data: dict[str, Any] = {**body.model_dump(), "created_at": created_at}
        course_id: Optional[int] = dbCreateCourse(conn, course_data)
        if course_id is None:
            raise HTTPException(status_code=500, detail="Failed to create course")
        
        return CourseOut(
            courseId=course_id,
            createdAt=created_at,
            **body.model_dump()
        )
    finally:
        conn.close()

@app.get(
    "/v1/workwise/courses",
    response_model=List[CourseOut],
    tags=["courses"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/courses")))]
)
def listCourses():
    conn = getDatabase()
    try:
        courses = getCourses(conn)
        created_at = datetime.now(timezone.utc).isoformat()
        return [CourseOut(
            courseId=c["course_id"],
            createdAt=c["created_at"] or created_at,
            **{k: v for k, v in c.items() if k not in ["course_id", "created_at"]}
        ) for c in courses]
    finally:
        conn.close()

# Worker_Courses (tagged "worker_courses")
@app.post(
    "/v1/workwise/worker_courses",
    response_model=WorkerCourseOut,
    tags=["worker_courses"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/worker_courses")))]
)
def enrollWorkerInCourse(body: WorkerCourseIn, current_worker_id: int = 1):
    conn = getDatabase()
    try:
        enrollment_date = datetime.now(timezone.utc).isoformat()
        enrollment_data: dict[str, Any] = {"worker_id": current_worker_id, "course_id": body.course_id, "enrollment_date": enrollment_date}
        enrollment_id = dbEnrollWorkerInCourse(conn, enrollment_data)
        if enrollment_id is None:
            raise HTTPException(status_code=500, detail="Failed to enroll in course")
        
        return WorkerCourseOut(
            enrollmentId=enrollment_id,
            workerId=current_worker_id,
            enrollment_date=enrollment_date,
            course_id=body.course_id,
            completionStatus="enrolled",
            completionPercentage=0.0,
            certificateEarned=False
        )
    finally:
        conn.close()

@app.get(
    "/v1/workwise/worker_courses",
    response_model=List[WorkerCourseOut],
    tags=["worker_courses"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/worker_courses")))]
)
def listWorkerCourses(worker_id: int = 1):
    conn = getDatabase()
    try:
        enrollments = getWorkerCourses(conn, worker_id)
        enrollment_date = datetime.now(timezone.utc).isoformat()
        return [WorkerCourseOut(
            enrollmentId=e["enrollment_id"],
            workerId=e["worker_id"],
            enrollment_date=e["enrollment_date"] or enrollment_date,
            course_id=e["course_id"],
            completionStatus=e["completion_status"] or "enrolled",
            completionPercentage=e["completion_percentage"] or 0.0,
            certificateEarned=e["certificate_earned"] or False
        ) for e in enrollments]
    finally:
        conn.close()

# Governments (tagged "governments")
@app.post(
    "/v1/workwise/governments",
    response_model=GovernmentOut,
    tags=["governments"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/governments")))]
)
def createGovernment(body: GovernmentIn):
    conn = getDatabase()
    try:
        if governmentExists(conn, body.department_name):
            raise HTTPException(status_code=409, detail="Department name already exists")

        created_at = datetime.now(timezone.utc).isoformat()
        gov_data: dict[str, Any] = {**body.model_dump(), "created_at": created_at, "updated_at": created_at}
        gov_id: Optional[int] = dbCreateGovernment(conn, gov_data)
        if gov_id is None:
            raise HTTPException(status_code=500, detail="Failed to create government")
        
        return GovernmentOut(
            governmentId=gov_id,
            createdAt=created_at,
            updatedAt=created_at,
            **body.model_dump()
        )
    finally:
        conn.close()

@app.get(
    "/v1/workwise/governments",
    response_model=List[GovernmentOut],
    tags=["governments"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/governments")))]
)
def listGovernments():
    conn = getDatabase()
    try:
        govs = getGovernments(conn)
        created_at = datetime.now(timezone.utc).isoformat()
        return [GovernmentOut(
            governmentId=g["government_id"],
            createdAt=g["created_at"] or created_at,
            updatedAt=g["updated_at"] or created_at,
            **{k: v for k, v in g.items() if k not in ["government_id", "created_at", "updated_at"]}
        ) for g in govs]
    finally:
        conn.close()

# Government Programs (tagged "government_programs")
@app.post(
    "/v1/workwise/government_programs",
    response_model=GovernmentProgramOut,
    tags=["government_programs"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/government_programs")))]
)
def createGovernmentProgram(body: GovernmentProgramIn):
    conn = getDatabase()
    try:
        # Verify government exists
        if not getGovernments(conn) or body.government_id not in [g["government_id"] for g in getGovernments(conn)]:
            raise HTTPException(status_code=400, detail="Government ID does not exist")

        created_at = datetime.now(timezone.utc).isoformat()
        program_data: dict[str, Any] = {**body.model_dump(), "created_at": created_at}
        program_id: Optional[int] = dbCreateGovernmentProgram(conn, program_data)
        if program_id is None:
            raise HTTPException(status_code=500, detail="Failed to create program")
        
        return GovernmentProgramOut(
            programId=program_id,
            createdAt=created_at,
            **body.model_dump()
        )
    finally:
        conn.close()

@app.get(
    "/v1/workwise/government_programs",
    response_model=List[GovernmentProgramOut],
    tags=["government_programs"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/government_programs")))]
)
def listGovernmentPrograms(government_id: Optional[int] = None):
    conn = getDatabase()
    try:
        programs = getGovernmentPrograms(conn, government_id)
        created_at = datetime.now(timezone.utc).isoformat()
        return [GovernmentProgramOut(
            programId=p["program_id"],
            createdAt=p["created_at"] or created_at,
            **{k: v for k, v in p.items() if k not in ["program_id", "created_at"]}
        ) for p in programs]
    finally:
        conn.close()

# Training Institutions (tagged "training_institutions")
@app.post(
    "/v1/workwise/training_institutions",
    response_model=TrainingInstitutionOut,
    tags=["training_institutions"],
    dependencies=[Depends(requireEndpointToken(getToken("POST", "/v1/workwise/training_institutions")))]
)
def createTrainingInstitution(body: TrainingInstitutionIn):
    conn = getDatabase()
    try:
        if trainingInstitutionExists(conn, body.name):
            raise HTTPException(status_code=409, detail="Institution name already exists")

        created_at = datetime.now(timezone.utc).isoformat()
        inst_data: dict[str, Any] = {**body.model_dump(), "created_at": created_at, "is_active": 1}
        inst_id: Optional[int] = dbCreateTrainingInstitution(conn, inst_data)
        if inst_id is None:
            raise HTTPException(status_code=500, detail="Failed to create institution")
        
        return TrainingInstitutionOut(
            institutionId=inst_id,
            isActive=True,
            createdAt=created_at,
            **body.model_dump()
        )
    finally:
        conn.close()

@app.get(
    "/v1/workwise/training_institutions",
    response_model=List[TrainingInstitutionOut],
    tags=["training_institutions"],
    dependencies=[Depends(requireEndpointToken(getToken("GET", "/v1/workwise/training_institutions")))]
)
def listTrainingInstitutions():
    conn = getDatabase()
    try:
        insts = getTrainingInstitutions(conn)
        created_at = datetime.now(timezone.utc).isoformat()
        return [TrainingInstitutionOut(
            institutionId=i["institution_id"],
            isActive=bool(i["is_active"]),
            createdAt=i["created_at"] or created_at,
            **{k: v for k, v in i.items() if k not in ["institution_id", "is_active", "created_at"]}
        ) for i in insts]
    finally:
        conn.close()

@app.get(
    "/v1/geocode",
    tags=["geolocation"],
    dependencies=[Depends(requireEndpointToken(endpointTokens.get("GET:/v1/geocode") or "GEOCODEFREE001"))]  # Optional token
)
def geocodeAddress(address: str) -> dict[str, str | float | int]:  # Query param: ?address="123 Main St, New York"
    if not address:
        raise HTTPException(status_code=400, detail="Address parameter required")
    
    # Nominatim API call (free, rate-limited to 1/sec; user-agent required)
    url = "https://nominatim.openstreetmap.org/search"
    params: dict[str, str | int] = {
        "q": address,
        "format": "json",
        "limit": 1,  # Top result
        "addressdetails": 1  # Include full details
    }
    headers = {"User-Agent": "WorkwiseAPI/1.0 (your.email@example.com)"}  # Required; replace with yours
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # Raise on 4xx/5xx
        data = response.json()
        
        if not data:
            raise HTTPException(status_code=404, detail="Address not found")
        
        result = data[0]
        return {
            "address": result.get("display_name", address),
            "lat": float(result["lat"]),
            "lon": float(result["lon"]),
            "formatted_address": result.get("display_name"),
            "place_type": result.get("type", "unknown"),
            "confidence": int(result.get("importance", 0))  # OSM confidence score
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Geocoding failed: {str(e)}")