import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional, Dict

from jose import JWTError, jwt

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel

from Database.db import (
    getTrainingInstitutions, getDatabase, trainingInstitutionExists,
    userExists, getUsersDetails, unionExists, getUnions, workerInUnion, getUnionMembers,
    createWorker as dbCreateWorker, getWorkers, createEmployer as dbCreateEmployer, getEmployers,
    createJob as dbCreateJob, getJobs, createApplication as dbCreateApplication, getApplications,
    getCourses, getWorkerCourses, enrollWorkerInCourse as dbEnrollWorkerInCourse, createCourse as dbCreateCourse,
    governmentExists, createGovernment as dbCreateGovernment, getGovernments, createGovernmentProgram as dbCreateGovernmentProgram,
    getGovernmentPrograms, createTrainingInstitution as dbCreateTrainingInstitution
)
from Models.models import (
    RegisterIn, RegisterOut, UnionIn, UnionOut,
    UnionMemberIn, UnionMemberOut, WorkerIn, WorkerOut,
    EmployerIn, EmployerOut, JobIn, JobOut, ApplicationIn, ApplicationOut,
    CourseIn, CourseOut, WorkerCourseIn, WorkerCourseOut, GovernmentIn,
    GovernmentOut, GovernmentProgramIn, GovernmentProgramOut, TrainingInstitutionIn, TrainingInstitutionOut
)

load_dotenv()

# uvicorn main:app --reload --host 0.0.0.0 --port 8000

# FastAPI app and helpers
app = FastAPI()
templates = Jinja2Templates(directory="templates")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Config (from .env)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/workwise/user")

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    user_id: int
    role: Optional[str] = None

class LoginIn(BaseModel):
    usernameOrEmail: str
    password: str

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), conn: Any = Depends(getDatabase)) -> Dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = getUsersDetails(conn, str(user_id))
    if user is None:
        raise credentials_exception
    return user

@app.post(
    "/v1/workwise/user",
    response_model=Token,
    tags=["auth"],
)
def login(body: LoginIn):
    conn = getDatabase()
    try:
        row = getUsersDetails(conn, body.usernameOrEmail)
        if not row or not pwd.verify(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"user_id": row["user_id"], "role": row.get("role")},
            expires_delta=access_token_expires
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    finally:
        conn.close()

@app.get("/v1/ping")
def ping() -> Dict[str, Any]:
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}

# Accounts
@app.post(
    "/v1/workwise/account",
    response_model=RegisterOut,
    tags=["auth"],
    dependencies=[Depends(get_current_user)]
)
def register(body: RegisterIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        if userExists(conn, body.username, body.email):
            raise HTTPException(status_code=409, detail="Username or email already exists")

        hashed = pwd.hash(body.password)
        created_at = datetime.now(timezone.utc).isoformat()

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, role, created_at, is_active)
            VALUES (?, ?, ?, 'user', ?, 1)
            """,
            (body.username, body.email, hashed, created_at)
        )
        conn.commit()
        user_id = cur.lastrowid
        if user_id is None:
            raise HTTPException(status_code=500, detail="Failed to create user")

        return RegisterOut(userId=user_id, username=body.username, email=body.email, role="user", isActive=True, createdAt=created_at)
    finally:
        conn.close()

# Unions
@app.get(
    "/v1/workwise/unions",
    response_model=List[UnionOut],
    tags=["unions"],
    dependencies=[Depends(get_current_user)]
)
def listUnions(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        unions = getUnions(conn)
        return [UnionOut(**u) for u in unions]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/unions",
    response_model=UnionOut,
    tags=["unions"],
    dependencies=[Depends(get_current_user)]
)
def createUnion(body: UnionIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        if unionExists(conn, body.register_num):
            raise HTTPException(status_code=409, detail="Union registration number already exists")
        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO unions (register_num, sector_info, membership_size, is_active_council, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (body.register_num, body.sector_info, body.membership_size, body.is_active_council, created_at)
        )
        conn.commit()
        union_id = cur.lastrowid
        return UnionOut(union_id=union_id, register_num=body.register_num, sector_info=body.sector_info, membership_size=body.membership_size, is_active_council=body.is_active_council, created_at=created_at) # pyright: ignore[reportCallIssue]
    finally:
        conn.close()

# Union members
@app.get(
    "/v1/workwise/union_members",
    response_model=List[UnionMemberOut],
    tags=["union_members"],
    dependencies=[Depends(get_current_user)]
)
def listUnionMembers(union_id: Optional[int] = None, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        members = getUnionMembers(conn, union_id)
        return [UnionMemberOut(**m) for m in members]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/union_members",
    response_model=UnionMemberOut,
    tags=["union_members"],
    dependencies=[Depends(get_current_user)]
)
def addUnionMember(body: UnionMemberIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        if workerInUnion(conn, body.worker_id, body.union_id):
            raise HTTPException(status_code=409, detail="Worker is already a member of this union")
        membership_num = body.membership_num or f"MEM-{body.worker_id}-{body.union_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO union_members (worker_id, union_id, membership_num, status)
            VALUES (?, ?, ?, ?)
            """,
            (body.worker_id, body.union_id, membership_num, body.status or "active")
        )
        conn.commit()
        membership_id = cur.lastrowid
        if membership_id is None:
            raise HTTPException(status_code=500, detail="Failed to create union membership")
        return UnionMemberOut(membershipId=membership_id, worker_id=body.worker_id, union_id=body.union_id, membership_num=membership_num, status=body.status or "active")
    finally:
        conn.close()

# Workers
@app.post(
    "/v1/workwise/workers",
    response_model=WorkerOut,
    tags=["workers"],
    dependencies=[Depends(get_current_user)]
)
def createWorker(body: WorkerIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        row = getUsersDetails(conn, current_user["user_id"])
        if not row or row.get("role") != "worker":
            raise HTTPException(status_code=400, detail="User must exist with 'worker' role")
        worker_data = {"user_id": current_user["user_id"], **body.model_dump()}
        worker_id = dbCreateWorker(conn, worker_data)
        if worker_id is None:
            raise HTTPException(status_code=500, detail="Failed to create worker")
        created_at = datetime.now(timezone.utc).isoformat()
        return WorkerOut(workerId=worker_id, userId=current_user["user_id"], createdAt=created_at, updatedAt=created_at, **body.model_dump())
    finally:
        conn.close()

@app.get(
    "/v1/workwise/workers",
    response_model=List[WorkerOut],
    tags=["workers"],
    dependencies=[Depends(get_current_user)]
)
def listWorkers(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        rows = getWorkers(conn)
        return [WorkerOut(**r) for r in rows]
    finally:
        conn.close()

# Employers
@app.post(
    "/v1/workwise/employers",
    response_model=EmployerOut,
    tags=["employers"],
    dependencies=[Depends(get_current_user)]
)
def createEmployer(body: EmployerIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        row = getUsersDetails(conn, current_user["user_id"])
        if not row or row.get("role") != "employer":
            raise HTTPException(status_code=400, detail="User must exist with 'employer' role")
        employer_data = {"user_id": current_user["user_id"], **body.model_dump()}
        employer_id = dbCreateEmployer(conn, employer_data)
        if employer_id is None:
            raise HTTPException(status_code=500, detail="Failed to create employer")
        created_at = datetime.now(timezone.utc).isoformat()
        return EmployerOut(employerId=employer_id, userId=current_user["user_id"], createdAt=created_at, **body.model_dump())
    finally:
        conn.close()

@app.get(
    "/v1/workwise/employers",
    response_model=List[EmployerOut],
    tags=["employers"],
    dependencies=[Depends(get_current_user)]
)
def listEmployers(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        rows = getEmployers(conn)
        return [EmployerOut(**r) for r in rows]
    finally:
        conn.close()

# Jobs
@app.post(
    "/v1/workwise/jobs",
    response_model=JobOut,
    tags=["jobs"],
    dependencies=[Depends(get_current_user)]
)
def createJob(body: JobIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        employer_id = current_user["user_id"]
        posted_at = datetime.now(timezone.utc).isoformat()
        job_data: Dict[str, Any] = {"employer_id": employer_id, **body.model_dump(), "posted_at": posted_at}
        job_id = dbCreateJob(conn, job_data)
        if job_id is None:
            raise HTTPException(status_code=500, detail="Failed to create job")
        return JobOut(jobId=job_id, employerId=employer_id, postedAt=posted_at, **body.model_dump())
    finally:
        conn.close()

@app.get(
    "/v1/workwise/jobs",
    response_model=List[JobOut],
    tags=["jobs"],
    dependencies=[Depends(get_current_user)]
)
def listJobs(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        jobs = getJobs(conn)
        return [JobOut(**j) for j in jobs]
    finally:
        conn.close()

# Applications
@app.post(
    "/v1/workwise/applications",
    response_model=ApplicationOut,
    tags=["applications"],
    dependencies=[Depends(get_current_user)]
)
def createApplication(body: ApplicationIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        applied_at = datetime.now(timezone.utc).isoformat()
        app_data: Dict[str, Any] = {"job_id": body.job_id, "worker_id": current_user["user_id"], **body.model_dump(), "applied_at": applied_at}
        app_id = dbCreateApplication(conn, app_data)
        if app_id is None:
            raise HTTPException(status_code=500, detail="Failed to create application")
        return ApplicationOut(applicationId=app_id, workerId=current_user["user_id"], appliedAt=applied_at, job_id=body.job_id, matchScore=0.0, **body.model_dump())
    finally:
        conn.close()

@app.get(
    "/v1/workwise/applications",
    response_model=List[ApplicationOut],
    tags=["applications"],
    dependencies=[Depends(get_current_user)]
)
def listApplications(worker_id: Optional[int] = None, job_id: Optional[int] = None, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        apps = getApplications(conn, worker_id=worker_id, job_id=job_id)
        return [ApplicationOut(**a) for a in apps]
    finally:
        conn.close()

# Courses
@app.post(
    "/v1/workwise/courses",
    response_model=CourseOut,
    tags=["courses"],
    dependencies=[Depends(get_current_user)]
)
def createCourse(body: CourseIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        created_at = datetime.now(timezone.utc).isoformat()
        course_data: Dict[str, Any] = {**body.model_dump(), "created_at": created_at}
        course_id = dbCreateCourse(conn, course_data)
        if course_id is None:
            raise HTTPException(status_code=500, detail="Failed to create course")
        return CourseOut(courseId=course_id, createdAt=created_at, **body.model_dump())
    finally:
        conn.close()

@app.get(
    "/v1/workwise/courses",
    response_model=List[CourseOut],
    tags=["courses"],
    dependencies=[Depends(get_current_user)]
)
def listCourses(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        courses = getCourses(conn)
        created_at = datetime.now(timezone.utc).isoformat()
        return [CourseOut(courseId=c["course_id"], createdAt=c.get("created_at") or created_at, **{k: v for k, v in c.items() if k not in ["course_id", "created_at"]}) for c in courses]
    finally:
        conn.close()

# Worker courses
@app.post(
    "/v1/workwise/worker_courses",
    response_model=WorkerCourseOut,
    tags=["worker_courses"],
    dependencies=[Depends(get_current_user)]
)
def enrollWorkerInCourse(body: WorkerCourseIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        enrollment_date = datetime.now(timezone.utc).isoformat()
        enrollment_data: Dict[str, Any] = {"worker_id": current_user["user_id"], "course_id": body.course_id, "enrollment_date": enrollment_date}
        enrollment_id = dbEnrollWorkerInCourse(conn, enrollment_data)
        if enrollment_id is None:
            raise HTTPException(status_code=500, detail="Failed to enroll in course")
        return WorkerCourseOut(enrollmentId=enrollment_id, workerId=current_user["user_id"], enrollmentDate=enrollment_date, courseId=body.course_id, completionStatus="enrolled", completionPercentage=0.0, certificateEarned=False) # pyright: ignore[reportCallIssue]
    finally:
        conn.close()

@app.get(
    "/v1/workwise/worker_courses",
    response_model=List[WorkerCourseOut],
    tags=["worker_courses"],
    dependencies=[Depends(get_current_user)]
)
def listWorkerCourses(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        rows = getWorkerCourses(conn, current_user["user_id"])
        return [WorkerCourseOut(**r) for r in rows]
    finally:
        conn.close()

# Governments
@app.post(
    "/v1/workwise/governments",
    response_model=GovernmentOut,
    tags=["governments"],
    dependencies=[Depends(get_current_user)]
)
def createGovernment(body: GovernmentIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        if governmentExists(conn, body.department_name):
            raise HTTPException(status_code=409, detail="Department name already exists")
        created_at = datetime.now(timezone.utc).isoformat()
        gov_data: Dict[str, Any] = {**body.model_dump(), "created_at": created_at, "updated_at": created_at}
        gov_id = dbCreateGovernment(conn, gov_data)
        if gov_id is None:
            raise HTTPException(status_code=500, detail="Failed to create government")
        return GovernmentOut(governmentId=gov_id, createdAt=created_at, updatedAt=created_at, **body.model_dump())
    finally:
        conn.close()

@app.get(
    "/v1/workwise/governments",
    response_model=List[GovernmentOut],
    tags=["governments"],
    dependencies=[Depends(get_current_user)]
)
def listGovernments(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        govs = getGovernments(conn)
        return [GovernmentOut(**g) for g in govs]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/government_programs",
    response_model=GovernmentProgramOut,
    tags=["government_programs"],
    dependencies=[Depends(get_current_user)]
)
def createGovernmentProgram(body: GovernmentProgramIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        govs = getGovernments(conn)
        if body.government_id not in [g["government_id"] for g in govs]:
            raise HTTPException(status_code=400, detail="Government ID does not exist")
        created_at = datetime.now(timezone.utc).isoformat()
        program_data: Dict[str, Any] = {**body.model_dump(), "created_at": created_at}
        program_id = dbCreateGovernmentProgram(conn, program_data)
        if program_id is None:
            raise HTTPException(status_code=500, detail="Failed to create program")
        return GovernmentProgramOut(programId=program_id, createdAt=created_at, **body.model_dump())
    finally:
        conn.close()

@app.get(
    "/v1/workwise/government_programs",
    response_model=List[GovernmentProgramOut],
    tags=["government_programs"],
    dependencies=[Depends(get_current_user)]
)
def listGovernmentPrograms(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        progs = getGovernmentPrograms(conn)
        return [GovernmentProgramOut(**p) for p in progs]
    finally:
        conn.close()

# Training institutions
@app.post(
    "/v1/workwise/training_institutions",
    response_model=TrainingInstitutionOut,
    tags=["training_institutions"],
    dependencies=[Depends(get_current_user)]
)
def createTrainingInstitution(body: TrainingInstitutionIn, current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        if trainingInstitutionExists(conn, body.name):
            raise HTTPException(status_code=409, detail="Institution name already exists")
        created_at = datetime.now(timezone.utc).isoformat()
        inst_data: Dict[str, Any] = {**body.model_dump(), "created_at": created_at, "is_active": 1}
        inst_id = dbCreateTrainingInstitution(conn, inst_data)
        if inst_id is None:
            raise HTTPException(status_code=500, detail="Failed to create institution")
        return TrainingInstitutionOut(institutionId=inst_id, isActive=True, createdAt=created_at, **body.model_dump())
    finally:
        conn.close()

@app.get(
    "/v1/workwise/training_institutions",
    response_model=List[TrainingInstitutionOut],
    tags=["training_institutions"],
    dependencies=[Depends(get_current_user)]
)
def listTrainingInstitutions(current_user: Dict[str, Any] = Depends(get_current_user)):
    conn = getDatabase()
    try:
        insts = getTrainingInstitutions(conn)
        created_at = datetime.now(timezone.utc).isoformat()
        return [TrainingInstitutionOut(institutionId=i["institution_id"], isActive=bool(i["is_active"]), createdAt=i.get("created_at") or created_at, **{k: v for k, v in i.items() if k not in ["institution_id", "is_active", "created_at"]}) for i in insts]
    finally:
        conn.close()

# Geocode helper
@app.get(
    "/v1/geocode",
    tags=["geolocation"],
)
def geocodeAddress(address: str) -> Dict[str, Any]:
    if not address:
        raise HTTPException(status_code=400, detail="Address parameter required")

    url = "https://nominatim.openstreetmap.org/search"
    params: Dict[str, Any] = {"q": address, "format": "json", "limit": 1, "addressdetails": 1}
    headers: Dict[str, str] = {"User-Agent": "WorkwiseAPI/1.0 (your.email@example.com)"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
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
            "confidence": int(result.get("importance", 0))
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Geocoding failed: {str(e)}")

# Custom exception handler
@app.exception_handler(HTTPException)
async def customHttpExceptionHandler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        accepts_html = "text/html" in request.headers.get("accept", "").lower()
        if accepts_html:
            return templates.TemplateResponse("401.html", {"request": request}, status_code=401)
        return JSONResponse({"detail": exc.detail or "Unauthorized"}, status_code=401)
    # fallback to default
    from fastapi.exception_handlers import http_exception_handler as defaultHttpHandler
    return await defaultHttpHandler(request, exc)