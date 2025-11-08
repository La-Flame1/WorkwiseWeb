from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any, List, Optional
import os
import base64
import uuid

from fastapi import FastAPI, HTTPException, Depends, Request, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security.api_key import APIKeyHeader
from fastapi.exception_handlers import http_exception_handler as defaultHttpHandler
from passlib.context import CryptContext

from Models.models import (
    RegisterIn, RegisterOut, LoginIn, LoginOut,
    UserProfileOut, UserProfileUpdateIn, ProfileImageUploadOut,
    CVOut, CVUploadOut,
    QualificationIn, QualificationOut, QualificationUpdateIn,
    UserStatsOut, SavedJobIn, SavedJobOut,
    UnionIn, UnionOut, UnionMemberIn, UnionMemberOut
)

from Database.db import (
    initDatabase, getDatabase, userExists, getUsersDetails, getUserById,
    updateUserProfile, getUserCVs, addCV, deleteCV, setPrimaryCV,
    getUserQualifications, addQualification, updateQualification, deleteQualification,
    getUserApplicationsCount, getUserSavedJobsCount, getSavedJobs, addSavedJob, deleteSavedJob,
    unionExists, getUnions, workerInUnion, getUnionMembers
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "profile_images"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "cvs"), exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    initDatabase()
    yield
    # Shutdown (if needed in the future)

app = FastAPI(
    title="Workwise API",
    version="2.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "auth", "description": "Authentication endpoints"},
        {"name": "profile", "description": "User profile management"},
        {"name": "cv", "description": "CV/Resume management"},
        {"name": "qualifications", "description": "Educational qualifications"},
        {"name": "stats", "description": "User statistics"},
        {"name": "saved_jobs", "description": "Saved jobs management"},
        {"name": "unions", "description": "Union management"},
        {"name": "union_members", "description": "Union membership management"}
    ]
)

templates = Jinja2Templates(directory="Templates")
endpoint_token = APIKeyHeader(name="X-Endpoint-Token")

endpointTokens = {
    # Auth
    "POST:/v1/workwise/account": "USNACCTOK123",
    "POST:/v1/workwise/user": "USNDPNQNKW",
    
    # Profile
    "GET:/v1/workwise/profile": "PROFILEGETTOK456",
    "PUT:/v1/workwise/profile": "PROFILEUPDATETOK789",
    "POST:/v1/workwise/profile/image": "PROFILEIMGTOK012",
    
    # CV
    "GET:/v1/workwise/cvs": "CVLISTTOK345",
    "POST:/v1/workwise/cvs": "CVUPLOADTOK678",
    "DELETE:/v1/workwise/cvs": "CVDELETETOK901",
    "PUT:/v1/workwise/cvs/primary": "CVPRIMARYTOK234",
    
    # Qualifications
    "GET:/v1/workwise/qualifications": "QUALLISTTOK567",
    "POST:/v1/workwise/qualifications": "QUALADDTOK890",
    "PUT:/v1/workwise/qualifications": "QUALUPDATETOK123",
    "DELETE:/v1/workwise/qualifications": "QUALDELETETOK456",
    
    # Stats
    "GET:/v1/workwise/stats": "STATSTOK789",
    
    # Saved Jobs
    "GET:/v1/workwise/saved-jobs": "SAVEDLISTTOK012",
    "POST:/v1/workwise/saved-jobs": "SAVEDADDTOK345",
    "DELETE:/v1/workwise/saved-jobs": "SAVEDDELETETOK678",
    
    # Unions
    "GET:/v1/workwise/unions": "UNIONLISTTOK456",
    "POST:/v1/workwise/unions": "UNIONCREATETOK789",
    "GET:/v1/workwise/union_members": "MEMBERLISTTOK012",
    "POST:/v1/workwise/union_members": "MEMBERADDTOK345",
}

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

# ========== AUTH ENDPOINTS ==========
@app.post(
    "/v1/workwise/account",
    response_model=RegisterOut,
    tags=["auth"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/account")]))]
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
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/user")]))]
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
def loginProbeHtml():
    raise HTTPException(status_code=401, detail="Missing or invalid endpoint token")

# ========== PROFILE ENDPOINTS ==========
@app.get(
    "/v1/workwise/profile/{user_id}",
    response_model=UserProfileOut,
    tags=["profile"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/profile")]))]
)
def getProfile(user_id: int):
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserProfileOut(
            userId=user["user_id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            profileImage=user["profile_image"],
            profileName=user["profile_name"],
            profileBio=user["profile_bio"],
            phoneNumber=user["phone_number"],
            location=user["location"],
            createdAt=user["created_at"],
            updatedAt=user["updated_at"]
        )
    finally:
        conn.close()

@app.put(
    "/v1/workwise/profile/{user_id}",
    response_model=UserProfileOut,
    tags=["profile"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("PUT", "/v1/workwise/profile")]))]
)
def updateProfile(user_id: int, body: UserProfileUpdateIn):
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        update_data = body.model_dump(exclude_unset=True)
        update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Convert camelCase to snake_case for database
        db_data = {}
        field_mapping = {
            'profileName': 'profile_name',
            'profileBio': 'profile_bio',
            'phoneNumber': 'phone_number',
            'location': 'location',
            'updated_at': 'updated_at'
        }
        for key, value in update_data.items():
            db_key = field_mapping.get(key, key)
            db_data[db_key] = value
        
        if not updateUserProfile(conn, user_id, db_data):
            raise HTTPException(status_code=500, detail="Failed to update profile")
        
        # Get updated user
        updated_user = getUserById(conn, user_id)
        return UserProfileOut(
            userId=updated_user["user_id"],
            username=updated_user["username"],
            email=updated_user["email"],
            role=updated_user["role"],
            profileImage=updated_user["profile_image"],
            profileName=updated_user["profile_name"],
            profileBio=updated_user["profile_bio"],
            phoneNumber=updated_user["phone_number"],
            location=updated_user["location"],
            createdAt=updated_user["created_at"],
            updatedAt=updated_user["updated_at"]
        )
    finally:
        conn.close()

@app.post(
    "/v1/workwise/profile/{user_id}/image",
    response_model=ProfileImageUploadOut,
    tags=["profile"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/profile/image")]))]
)
async def uploadProfileImage(user_id: int, file: UploadFile = File(...)):
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed")
        
        # Generate unique filename
        file_extension = file.filename.split(".")[-1] if file.filename else "jpg"
        unique_filename = f"{user_id}_{uuid.uuid4().hex}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, "profile_images", unique_filename)
        
        # Save file
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Update user profile with image path
        update_data = {
            'profile_image': file_path,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if not updateUserProfile(conn, user_id, update_data):
            # Clean up uploaded file if database update fails
            os.remove(file_path)
            raise HTTPException(status_code=500, detail="Failed to update profile image")
        
        return ProfileImageUploadOut(
            userId=user_id,
            profileImage=file_path,
            message="Profile image uploaded successfully"
        )
    finally:
        conn.close()

# ========== CV ENDPOINTS ==========
@app.get(
    "/v1/workwise/cvs/{user_id}",
    response_model=List[CVOut],
    tags=["cv"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/cvs")]))]
)
def listCVs(user_id: int):
    conn = getDatabase()
    try:
        cvs = getUserCVs(conn, user_id)
        return [CVOut(
            cvId=cv["cv_id"],
            userId=cv["user_id"],
            cvName=cv["cv_name"],
            filePath=cv["file_path"],
            fileSize=cv["file_size"],
            mimeType=cv["mime_type"],
            isPrimary=bool(cv["is_primary"]),
            uploadedAt=cv["uploaded_at"]
        ) for cv in cvs]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/cvs/{user_id}",
    response_model=CVUploadOut,
    tags=["cv"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/cvs")]))]
)
async def uploadCV(user_id: int, file: UploadFile = File(...), is_primary: bool = Form(False)):
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate file type
        allowed_types = ["application/pdf", "application/msword", 
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF and Word documents are allowed")
        
        # Generate unique filename
        file_extension = file.filename.split(".")[-1] if file.filename else "pdf"
        unique_filename = f"{user_id}_cv_{uuid.uuid4().hex}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, "cvs", unique_filename)
        
        # Save file
        contents = await file.read()
        file_size = len(contents)
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Add CV to database
        cv_data = {
            'user_id': user_id,
            'cv_name': file.filename or unique_filename,
            'file_path': file_path,
            'file_size': file_size,
            'mime_type': file.content_type,
            'is_primary': is_primary,
            'uploaded_at': datetime.now(timezone.utc).isoformat()
        }
        
        cv_id = addCV(conn, cv_data)
        if not cv_id:
            os.remove(file_path)
            raise HTTPException(status_code=500, detail="Failed to save CV")
        
        # If this is set as primary, unset others
        if is_primary:
            setPrimaryCV(conn, cv_id, user_id)
        
        return CVUploadOut(
            cvId=cv_id,
            cvName=file.filename or unique_filename,
            filePath=file_path,
            uploadedAt=cv_data['uploaded_at']
        )
    finally:
        conn.close()

@app.delete(
    "/v1/workwise/cvs/{user_id}/{cv_id}",
    tags=["cv"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("DELETE", "/v1/workwise/cvs")]))]
)
def removeCV(user_id: int, cv_id: int):
    conn = getDatabase()
    try:
        # Get CV details first to delete file
        cvs = getUserCVs(conn, user_id)
        cv_to_delete = next((cv for cv in cvs if cv["cv_id"] == cv_id), None)
        
        if not cv_to_delete:
            raise HTTPException(status_code=404, detail="CV not found")
        
        if deleteCV(conn, cv_id, user_id):
            # Delete file from filesystem
            if os.path.exists(cv_to_delete["file_path"]):
                os.remove(cv_to_delete["file_path"])
            return {"message": "CV deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete CV")
    finally:
        conn.close()

@app.put(
    "/v1/workwise/cvs/{user_id}/{cv_id}/primary",
    tags=["cv"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("PUT", "/v1/workwise/cvs/primary")]))]
)
def setAsPrimaryCV(user_id: int, cv_id: int):
    conn = getDatabase()
    try:
        if setPrimaryCV(conn, cv_id, user_id):
            return {"message": "CV set as primary successfully"}
        else:
            raise HTTPException(status_code=404, detail="CV not found")
    finally:
        conn.close()

# ========== QUALIFICATIONS ENDPOINTS ==========
@app.get(
    "/v1/workwise/qualifications/{user_id}",
    response_model=List[QualificationOut],
    tags=["qualifications"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/qualifications")]))]
)
def listQualifications(user_id: int):
    conn = getDatabase()
    try:
        qualifications = getUserQualifications(conn, user_id)
        return [QualificationOut(
            qualificationId=q["qualification_id"],
            userId=q["user_id"],
            qualificationType=q["qualification_type"],
            institution=q["institution"],
            fieldOfStudy=q["field_of_study"],
            qualificationName=q["qualification_name"],
            startDate=q["start_date"],
            endDate=q["end_date"],
            isCurrent=bool(q["is_current"]),
            gradeOrGpa=q["grade_or_gpa"],
            description=q["description"],
            createdAt=q["created_at"]
        ) for q in qualifications]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/qualifications/{user_id}",
    response_model=QualificationOut,
    tags=["qualifications"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/qualifications")]))]
)
def addNewQualification(user_id: int, body: QualificationIn):
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        qual_data = {
            'user_id': user_id,
            'qualification_type': body.qualificationType,
            'institution': body.institution,
            'field_of_study': body.fieldOfStudy,
            'qualification_name': body.qualificationName,
            'start_date': body.startDate,
            'end_date': body.endDate,
            'is_current': body.isCurrent,
            'grade_or_gpa': body.gradeOrGpa,
            'description': body.description,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        qual_id = addQualification(conn, qual_data)
        if not qual_id:
            raise HTTPException(status_code=500, detail="Failed to add qualification")
        
        return QualificationOut(
            qualificationId=qual_id,
            userId=user_id,
            qualificationType=body.qualificationType,
            institution=body.institution,
            fieldOfStudy=body.fieldOfStudy,
            qualificationName=body.qualificationName,
            startDate=body.startDate,
            endDate=body.endDate,
            isCurrent=body.isCurrent,
            gradeOrGpa=body.gradeOrGpa,
            description=body.description,
            createdAt=qual_data['created_at']
        )
    finally:
        conn.close()

@app.put(
    "/v1/workwise/qualifications/{user_id}/{qualification_id}",
    response_model=QualificationOut,
    tags=["qualifications"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("PUT", "/v1/workwise/qualifications")]))]
)
def editQualification(user_id: int, qualification_id: int, body: QualificationUpdateIn):
    conn = getDatabase()
    try:
        # Get existing qualification
        qualifications = getUserQualifications(conn, user_id)
        existing = next((q for q in qualifications if q["qualification_id"] == qualification_id), None)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Qualification not found")
        
        # Merge updates with existing data
        update_data = body.model_dump(exclude_unset=True)
        
        qual_data = {
            'qualification_type': update_data.get('qualificationType', existing['qualification_type']),
            'institution': update_data.get('institution', existing['institution']),
            'field_of_study': update_data.get('fieldOfStudy', existing['field_of_study']),
            'qualification_name': update_data.get('qualificationName', existing['qualification_name']),
            'start_date': update_data.get('startDate', existing['start_date']),
            'end_date': update_data.get('endDate', existing['end_date']),
            'is_current': update_data.get('isCurrent', bool(existing['is_current'])),
            'grade_or_gpa': update_data.get('gradeOrGpa', existing['grade_or_gpa']),
            'description': update_data.get('description', existing['description'])
        }
        
        if not updateQualification(conn, qualification_id, user_id, qual_data):
            raise HTTPException(status_code=500, detail="Failed to update qualification")
        
        return QualificationOut(
            qualificationId=qualification_id,
            userId=user_id,
            qualificationType=qual_data['qualification_type'],
            institution=qual_data['institution'],
            fieldOfStudy=qual_data['field_of_study'],
            qualificationName=qual_data['qualification_name'],
            startDate=qual_data['start_date'],
            endDate=qual_data['end_date'],
            isCurrent=qual_data['is_current'],
            gradeOrGpa=qual_data['grade_or_gpa'],
            description=qual_data['description'],
            createdAt=existing['created_at']
        )
    finally:
        conn.close()

@app.delete(
    "/v1/workwise/qualifications/{user_id}/{qualification_id}",
    tags=["qualifications"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("DELETE", "/v1/workwise/qualifications")]))]
)
def removeQualification(user_id: int, qualification_id: int):
    conn = getDatabase()
    try:
        if deleteQualification(conn, qualification_id, user_id):
            return {"message": "Qualification deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Qualification not found")
    finally:
        conn.close()

# ========== STATS ENDPOINTS ==========
@app.get(
    "/v1/workwise/stats/{user_id}",
    response_model=UserStatsOut,
    tags=["stats"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/stats")]))]
)
def getUserStats(user_id: int):
    conn = getDatabase()
    try:
        applications_count = getUserApplicationsCount(conn, user_id)
        saved_jobs_count = getUserSavedJobsCount(conn, user_id)
        
        return UserStatsOut(
            applicationsCount=applications_count,
            savedJobsCount=saved_jobs_count
        )
    finally:
        conn.close()

# ========== SAVED JOBS ENDPOINTS ==========
@app.get(
    "/v1/workwise/saved-jobs/{user_id}",
    response_model=List[SavedJobOut],
    tags=["saved_jobs"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/saved-jobs")]))]
)
def listSavedJobs(user_id: int):
    conn = getDatabase()
    try:
        jobs = getSavedJobs(conn, user_id)
        return [SavedJobOut(
            savedJobId=job["saved_job_id"],
            userId=job["user_id"],
            jobTitle=job["job_title"],
            companyName=job["company_name"],
            jobLocation=job["job_location"],
            salaryRange=job["salary_range"],
            jobDescription=job["job_description"],
            savedAt=job["saved_at"]
        ) for job in jobs]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/saved-jobs/{user_id}",
    response_model=SavedJobOut,
    tags=["saved_jobs"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/saved-jobs")]))]
)
def saveJob(user_id: int, body: SavedJobIn):
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        job_data = {
            'user_id': user_id,
            'job_title': body.jobTitle,
            'company_name': body.companyName,
            'job_location': body.jobLocation,
            'salary_range': body.salaryRange,
            'job_description': body.jobDescription,
            'saved_at': datetime.now(timezone.utc).isoformat()
        }
        
        job_id = addSavedJob(conn, job_data)
        if not job_id:
            raise HTTPException(status_code=500, detail="Failed to save job")
        
        return SavedJobOut(
            savedJobId=job_id,
            userId=user_id,
            jobTitle=body.jobTitle,
            companyName=body.companyName,
            jobLocation=body.jobLocation,
            salaryRange=body.salaryRange,
            jobDescription=body.jobDescription,
            savedAt=job_data['saved_at']
        )
    finally:
        conn.close()

@app.delete(
    "/v1/workwise/saved-jobs/{user_id}/{saved_job_id}",
    tags=["saved_jobs"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("DELETE", "/v1/workwise/saved-jobs")]))]
)
def removeSavedJob(user_id: int, saved_job_id: int):
    conn = getDatabase()
    try:
        if deleteSavedJob(conn, saved_job_id, user_id):
            return {"message": "Saved job deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Saved job not found")
    finally:
        conn.close()

# ========== UNION ENDPOINTS (existing) ==========
@app.get(
    "/v1/workwise/unions",
    response_model=List[UnionOut],
    tags=["unions"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/unions")]))]
)
def listUnions():
    conn = getDatabase()
    try:
        unions = getUnions(conn)
        return [UnionOut(
            unionId=union["union_id"],
            register_num=union["register_num"],
            sector_info=union["sector_info"],
            membership_size=union["membership_size"],
            is_active_council=bool(union["is_active_council"]),
            createdAt=union["created_at"]
        ) for union in unions]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/unions",
    response_model=UnionOut,
    tags=["unions"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/unions")]))]
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

@app.get(
    "/v1/workwise/union_members",
    response_model=List[UnionMemberOut],
    tags=["union_members"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/union_members")]))]
)
def listUnionMembers(union_id: Optional[int] = None):
    conn = getDatabase()
    try:
        members = getUnionMembers(conn, union_id)
        return [UnionMemberOut(
            membershipId=member["membership_id"],
            worker_id=member["worker_id"],
            union_id=member["union_id"],
            membership_num=member["membership_num"],
            status=member["status"]
        ) for member in members]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/union_members",
    response_model=UnionMemberOut,
    tags=["union_members"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/union_members")]))]
)
def addMemberToUnion(body: UnionMemberIn):
    conn = getDatabase()
    try:
        if workerInUnion(conn, body.worker_id, body.union_id):
            raise HTTPException(status_code=409, detail="Worker is already a member of this union")

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
        
        cur.execute("UPDATE unions SET membership_size = membership_size + 1 WHERE union_id = ?", (body.union_id,))
        conn.commit()
        
        return UnionMemberOut(
            membershipId=membership_id,
            worker_id=body.worker_id,
            union_id=body.union_id,
            membership_num=membership_num,
            status=body.status or "active"
        )
    finally:
        conn.close()
