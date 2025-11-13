from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any, List, Optional
import os
import uuid

from fastapi import FastAPI, HTTPException, Depends, Request, File, UploadFile
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

@app.post(
    "/v1/workwise/user",
    response_model=LoginOut,
    tags=["auth"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/user")]))]
)
def login(body: LoginIn):
    conn = getDatabase()
    try:
        user = getUsersDetails(conn, body.usernameOrEmail)   # <-- now returns dict with "id"
        if not user or not pwd.verify(body.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return LoginOut(
            userId=user["id"],          # <-- works
            username=user["username"],
            email=user["email"],
            role=user["role"]
        )
    finally:
        conn.close()

# ========== PROFILE ENDPOINTS ==========
@app.put(
    "/v1/workwise/profile/{user_id}",
    response_model=UserProfileOut,
    tags=["profile"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("PUT", "/v1/workwise/profile")]))]
)
def updateUserProfileEndpoint(user_id: int, update: UserProfileUpdateIn): # Renamed to avoid clash
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        updates: dict[str, Any] = {}
        if update.profileName is not None:
            updates["profileName"] = update.profileName
        if update.profileBio is not None:
            updates["profileBio"] = update.profileBio
        if update.phoneNumber is not None:
            updates["phoneNumber"] = update.phoneNumber
        if update.location is not None:
            updates["location"] = update.location
        if update.sideProjects is not None:
            updates["sideProjects"] = update.sideProjects
        
        # Add userId for the db function and set update timestamp
        updates["userId"] = user_id
        updates["updatedAt"] = datetime.now(timezone.utc).isoformat()
        
        if len(updates) > 2: # (userId and updatedAt are always present)
            updateUserProfile(conn, updates)  # Corrected call
        
        # Return updated profile by re-fetching
        updated_user_data = getUserById(conn, user_id)
        if not updated_user_data:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated profile")
            
        return UserProfileOut(**updated_user_data)
    finally:
        conn.close()

@app.get(
    "/v1/workwise/profile/{user_id}",
    response_model=UserProfileOut,
    tags=["profile"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/profile")]))]
)
def getUserProfile(user_id: int):
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserProfileOut(**user)
    finally:
        conn.close()

@app.post(
    "/v1/workwise/profile/{user_id}/image",
    response_model=ProfileImageUploadOut,
    tags=["profile"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/profile/image")]))]
)
def uploadProfileImage(user_id: int, file: UploadFile = File(...)):
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Save file
        ext = os.path.splitext(file.filename or "default.png")[1]
        filename = f"{uuid.uuid4()}{ext}"
        path = os.path.join(UPLOAD_DIR, "profile_images", filename)
        
        with open(path, "wb") as f:
            content = file.file.read()
            f.write(content)
        
        # Update DB
        cur = conn.cursor()
        cur.execute("UPDATE users SET profile_image = ? WHERE user_id = ?", (path, user_id))
        conn.commit()
        
        return ProfileImageUploadOut(
            userId=user_id,
            profileImage=path,
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
def route_list_user_cvs(user_id: int): # Renamed to avoid clash with imported db function
    conn = getDatabase()
    try:
        cvs = getUserCVs(conn, user_id) # This now correctly calls the db function
        return [CVOut(
            cvId=cv["cvId"],
            userId=cv["userId"],
            cvName=cv["cvName"],
            filePath=cv["filePath"],
            fileSize=cv.get("fileSize"),
            mimeType=cv.get("mimeType"),
            isPrimary=bool(cv["isPrimary"]),
            uploadedAt=cv["uploadedAt"]
        ) for cv in cvs]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/cvs/{user_id}",
    response_model=CVUploadOut,
    tags=["cv"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/cvs")]))]
)
def uploadCV(user_id: int, file: UploadFile = File(...)):
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Save file
        ext = os.path.splitext(file.filename or "default.pdf")[1]
        filename = f"{uuid.uuid4()}{ext}"
        path = os.path.join(UPLOAD_DIR, "cvs", filename)
        
        with open(path, "wb") as f:
            content = file.file.read()
            f.write(content)
        
        # Add to DB
        uploaded_at = datetime.now(timezone.utc).isoformat()
        cv_data: dict[str, Any] = {
            "userId": user_id,
            "cvName": file.filename,
            "filePath": path,
            "fileSize": os.path.getsize(path),
            "mimeType": file.content_type,
            "isPrimary": 0,  # Default
            "uploadedAt": uploaded_at
        }
        cv_id = addCV(conn, cv_data) # Corrected to pass camelCase keys
        if not cv_id:
            raise HTTPException(status_code=500, detail="Failed to upload CV")
        
        return CVUploadOut(
            cvId=cv_id,
            cvName=str(file.filename),
            filePath=path,
            uploadedAt=uploaded_at
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
        if deleteCV(conn, cv_id, user_id):
            return {"message": "CV deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="CV not found")
    finally:
        conn.close()

@app.put(
    "/v1/workwise/cvs/{user_id}/primary/{cv_id}",
    tags=["cv"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("PUT", "/v1/workwise/cvs/primary")]))]
)
def makePrimaryCV(user_id: int, cv_id: int):
    conn = getDatabase()
    try:
        if setPrimaryCV(conn, cv_id, user_id):
            return {"message": "CV set as primary"}
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
def route_list_user_qualifications(user_id: int): # Renamed to avoid clash
    conn = getDatabase()
    try:
        quals = getUserQualifications(conn, user_id) # This now correctly calls the db function
        return [QualificationOut(
            qualificationId=q["qualificationId"],
            userId=q["userId"],
            qualificationType=q["qualificationType"],
            institution=q["institution"],
            fieldOfStudy=q.get("fieldOfStudy"),
            qualificationName=q["qualificationName"],
            startDate=q.get("startDate"),
            endDate=q.get("endDate"),
            isCurrent=bool(q["isCurrent"]),
            gradeOrGpa=q.get("gradeOrGpa"),
            description=q.get("description"),
            createdAt=q["createdAt"]
        ) for q in quals]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/qualifications/{user_id}",
    response_model=QualificationOut,
    tags=["qualifications"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/qualifications")]))]
)
def addUserQualification(user_id: int, body: QualificationIn):
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        qual_data: dict[str, Any] = {
            "userId": user_id,
            "qualificationType": body.qualificationType,
            "institution": body.institution,
            "fieldOfStudy": body.fieldOfStudy,
            "qualificationName": body.qualificationName,
            "startDate": body.startDate,
            "endDate": body.endDate if not body.isCurrent else None,
            "isCurrent": int(body.isCurrent),
            "gradeOrGpa": body.gradeOrGpa,
            "description": body.description,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        qual_id = addQualification(conn, qual_data) # Corrected to pass camelCase keys
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
            createdAt=qual_data["createdAt"]
        )
    finally:
        conn.close()

@app.put(
    "/v1/workwise/qualifications/{user_id}/{qualification_id}",
    response_model=QualificationOut,
    tags=["qualifications"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("PUT", "/v1/workwise/qualifications")]))]
)
def updateUserQualification(user_id: int, qualification_id: int, body: QualificationUpdateIn): # This name is fine, no import clash
    conn = getDatabase()
    try:
        updates: dict[str, Any] = {}
        if body.qualificationType is not None: updates["qualificationType"] = body.qualificationType
        if body.institution is not None: updates["institution"] = body.institution
        if body.fieldOfStudy is not None: updates["fieldOfStudy"] = body.fieldOfStudy
        if body.qualificationName is not None: updates["qualificationName"] = body.qualificationName
        if body.startDate is not None: updates["startDate"] = body.startDate
        if body.endDate is not None: updates["endDate"] = body.endDate
        if body.isCurrent is not None: updates["isCurrent"] = int(body.isCurrent)
        if body.gradeOrGpa is not None: updates["gradeOrGpa"] = body.gradeOrGpa
        if body.description is not None: updates["description"] = body.description
        
        if updates:
            if not updateQualification(conn, qualification_id, user_id, updates):
                raise HTTPException(status_code=404, detail="Qualification not found or update failed")
        
        # Fetch the updated (or un-updated) qualification to return it
        quals = getUserQualifications(conn, user_id) # This now uses the DB function
        updated_qual = next((q for q in quals if q["qualificationId"] == qualification_id), None)
        
        if updated_qual:
            return QualificationOut(**updated_qual)
        else:
            raise HTTPException(status_code=404, detail="Qualification not found after update")
    finally:
        conn.close()

@app.delete(
    "/v1/workwise/qualifications/{user_id}/{qualification_id}",
    tags=["qualifications"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("DELETE", "/v1/workwise/qualifications")]))]
)
def removeUserQualification(user_id: int, qualification_id: int):
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
        user = getUserById(conn, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        apps_count = getUserApplicationsCount(conn, user_id)
        saved_count = getUserSavedJobsCount(conn, user_id)
        
        return UserStatsOut(
            applicationsCount=apps_count,
            savedJobsCount=saved_count
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
            savedJobId=job["savedJobId"],
            userId=job["userId"],
            jobTitle=job["jobTitle"],
            companyName=job["companyName"],
            jobLocation=job.get("jobLocation"),
            salaryRange=job.get("salaryRange"),
            jobDescription=job.get("jobDescription"),
            savedAt=job["savedAt"]
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
        
        saved_at = datetime.now(timezone.utc).isoformat()
        job_data: dict[str, Any] = {
            'userId': user_id,
            'jobTitle': body.jobTitle,
            'companyName': body.companyName,
            'jobLocation': body.jobLocation,
            'salaryRange': body.salaryRange,
            'jobDescription': body.jobDescription,
            'savedAt': saved_at
        }
        
        job_id = addSavedJob(conn, job_data) # Corrected to pass camelCase keys
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
            savedAt=saved_at
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

# ========== UNION ENDPOINTS ==========
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
        """, (body.register_num, body.sector_info, body.membership_size, int(body.is_active_council), created_at))
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