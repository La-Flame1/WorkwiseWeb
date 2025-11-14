from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any, List, Optional
import os
import uuid

from fastapi import FastAPI, HTTPException, Depends, Request, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security.api_key import APIKeyHeader
from fastapi.exception_handlers import http_exception_handler as defaultHttpHandler
from passlib.context import CryptContext
from fastapi.routing import APIRoute

from Models.models import (
    RegisterIn, RegisterOut, LoginIn, LoginOut,
    UserProfileOut, UserProfileUpdateIn, ProfileImageUploadOut, 
    CVOut, CVUploadOut,
    QualificationIn, QualificationOut, QualificationUpdateIn,
    UserStatsOut, SavedJobIn, SavedJobOut,
    BusinessIn, BusinessOut, JobIn, JobOut, JobListingOut, JobDetailOut,
    UnionIn, UnionOut, UnionMemberIn, UnionMemberOut,
    # 2. ADD NEW PASSWORD MODELS
    ForgotPasswordIn, ForgotPasswordOut,
    VerifyResetCodeIn, VerifyResetCodeOut,
    ResetPasswordIn, ResetPasswordOut, ApiResponse
)

from Database.db import (
    initDatabase, getDatabase, userExists, getUsersDetails, getUserById,
    updateUserProfile, getUserCVs, addCV, deleteCV, setPrimaryCV,
    getUserQualifications, addQualification, updateQualification, deleteQualification,
    getUserApplicationsCount, getUserSavedJobsCount, getSavedJobs, addSavedJob, deleteSavedJob,
    addBusiness, addJob, getActiveJobs, getJobById, searchJobs,
    unionExists, getUnions, workerInUnion, getUnionMembers,
    # 3. ADD NEW DB HELPERS
    emailExists, create_reset_code, verify_reset_code, reset_user_password
)

# ... (Upload directory setup is unchanged) ...
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "profile_images"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "cvs"), exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    initDatabase() 
    # Debug: list registered auth/reset routes to help diagnose 404s
    try:
        wanted = {"/v1/workwise/forgot-password", "/v1/workwise/verify-reset-code", "/v1/workwise/reset-password"}
        present: list[str] = []
        for r in app.routes:
            if isinstance(r, APIRoute) and r.path in wanted:
                present.append(f"{sorted(r.methods)} {r.path}")
        print("[Route Debug] Password reset related routes:")
        if present:
            for line in present:
                print("  -", line)
        else:
            print("  (None found - ensure module imported)")
    except Exception as e:
        print(f"[Route Debug] Error enumerating routes: {e}")
    yield

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
        {"name": "businesses", "description": "Manage businesses (Admin)"},
        {"name": "jobs", "description": "Manage and view job listings"},
        {"name": "unions", "description": "Union management"},
        {"name": "union_members", "description": "Union membership management"}
    ]
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

templates = Jinja2Templates(directory="Templates")
endpoint_token = APIKeyHeader(name="X-Endpoint-Token")

# 4. ADD NEW TOKENS
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
    
    # Job and Business Tokens
    "POST:/v1/workwise/businesses": "BUSIADDTOK111",
    "POST:/v1/workwise/jobs": "JOBADDTOK222",
    "GET:/v1/workwise/jobs": "JOBLISTTOK333",
    "GET:/v1/workwise/jobs/detail": "JOBDETAILTOK444",
    "GET:/v1/workwise/jobs/search": "JOBSEARCHTOK555",

    # Password Reset
    "POST:/v1/workwise/forgot-password": "FORGOTPASSTOK666",
    "POST:/v1/workwise/verify-reset-code": "VERIFYCODETOK777",
    "POST:/v1/workwise/reset-password": "RESETPASSTOK888",

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

# ... (Exception handler and ping are unchanged) ...
@app.exception_handler(HTTPException)
async def customHttpExceptionHandler(request: Request, exc: HTTPException):
    # ... (unchanged) ...
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
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        if userExists(conn, body.username, body.email):
            raise HTTPException(status_code=409, detail="Username or email already exists")
        hashed = pwd.hash(body.password)
        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, email, password_hash, role, created_at, is_active) VALUES (?, ?, ?, 'user', ?, 1)", (body.username, body.email, hashed, created_at))
        conn.commit()
        user_id = cur.lastrowid
        if user_id is None:
            raise HTTPException(status_code=500, detail="Failed to create user")
        return RegisterOut(userId=user_id, username=body.username, email=body.email, role="user", createdAt=created_at, isActive=True)
    finally:
        conn.close()

@app.post(
    "/v1/workwise/user",
    response_model=LoginOut,
    tags=["auth"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/user")]))]
)
def login(body: LoginIn):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        user = getUsersDetails(conn, body.usernameOrEmail)
        if not user or not pwd.verify(body.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return LoginOut(userId=user["id"], username=user["username"], email=user["email"], role=user["role"])
    finally:
        conn.close()

# --- 5. ADD NEW PASSWORD RESET ENDPOINTS ---

@app.post(
    "/v1/workwise/forgot-password",
    response_model=ForgotPasswordOut,
    tags=["auth"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/forgot-password")]))]
)
def forgot_password(body: ForgotPasswordIn):
    conn = getDatabase()
    try:
        if not emailExists(conn, body.email):
            # Still return 200 OK to prevent email enumeration
            print(f"Password reset attempt for non-existent email: {body.email}")
            return ForgotPasswordOut(message="If this email exists, a reset code has been sent.")
        
        # Generate and store code
        code = create_reset_code(conn, body.email)
        
        # --- In a real app, you would email the code here ---
        # send_email(body.email, "Your WorkWise Password Reset Code", f"Your code is: {code}")
        print(f"Password reset code for {body.email} is {code} (NOT SENT)")
        # ---
        
        return ForgotPasswordOut(message="If this email exists, a reset code has been sent.")
    finally:
        conn.close()

@app.post(
    "/v1/workwise/verify-reset-code",
    response_model=VerifyResetCodeOut,
    tags=["auth"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/verify-reset-code")]))]
)
def verify_code(body: VerifyResetCodeIn):
    conn = getDatabase()
    try:
        is_valid = verify_reset_code(conn, body.email, body.code)
        if is_valid:
            return VerifyResetCodeOut(valid=True, message="Code is valid")
        else:
            return VerifyResetCodeOut(valid=False, message="Invalid or expired code")
    finally:
        conn.close()

@app.post(
    "/v1/workwise/reset-password",
    response_model=ResetPasswordOut,
    tags=["auth"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/reset-password")]))]
)
def reset_password(body: ResetPasswordIn):
    conn = getDatabase()
    try:
        # Hash the new password
        new_hash = pwd.hash(body.newPassword)
        
        success = reset_user_password(conn, body.email, body.code, new_hash)
        
        if success:
            return ResetPasswordOut(success=True, message="Password reset successfully")
        else:
            raise HTTPException(status_code=400, detail="Invalid or expired code")
    finally:
        conn.close()

# --- END NEW PASSWORD RESET ENDPOINTS ---


# ========== PROFILE ENDPOINTS ==========
@app.put(
    "/v1/workwise/profile/{user_id}",
    response_model=UserProfileOut,
    tags=["profile"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("PUT", "/v1/workwise/profile")]))]
)
def updateUserProfileEndpoint(user_id: int, update: UserProfileUpdateIn):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user: raise HTTPException(status_code=404, detail="User not found")
        updates: dict[str, Any] = update.model_dump(exclude_unset=True)
        if not updates: return UserProfileOut(**user) # Return current if no changes
        updates["userId"] = user_id
        updates["updatedAt"] = datetime.now(timezone.utc).isoformat()
        updateUserProfile(conn, updates)
        updated_user_data = getUserById(conn, user_id)
        if not updated_user_data: raise HTTPException(status_code=500, detail="Failed to retrieve updated profile")
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
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user: raise HTTPException(status_code=404, detail="User not found")
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
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user: raise HTTPException(status_code=404, detail="User not found")
        ext = os.path.splitext(file.filename or "default.png")[1]
        filename = f"{uuid.uuid4()}{ext}"
        path = os.path.join(UPLOAD_DIR, "profile_images", filename)
        with open(path, "wb") as f: content = file.file.read(); f.write(content)
        cur = conn.cursor()
        cur.execute("UPDATE users SET profile_image = ? WHERE user_id = ?", (path, user_id))
        conn.commit()
        return ProfileImageUploadOut(userId=user_id, profileImage=path, message="Profile image uploaded successfully")
    finally:
        conn.close()

# ========== CV ENDPOINTS ==========
@app.get(
    "/v1/workwise/cvs/{user_id}",
    response_model=List[CVOut],
    tags=["cv"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/cvs")]))]
)
def route_list_user_cvs(user_id: int):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        cvs = getUserCVs(conn, user_id)
        return [CVOut(**cv) for cv in cvs]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/cvs/{user_id}",
    response_model=CVUploadOut,
    tags=["cv"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/cvs")]))]
)
def uploadCV(user_id: int, file: UploadFile = File(...)):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user: raise HTTPException(status_code=404, detail="User not found")
        ext = os.path.splitext(file.filename or "default.pdf")[1]
        filename = f"{uuid.uuid4()}{ext}"
        path = os.path.join(UPLOAD_DIR, "cvs", filename)
        with open(path, "wb") as f: content = file.file.read(); f.write(content)
        uploaded_at = datetime.now(timezone.utc).isoformat()
        cv_data: dict[str, Any] = {"userId": user_id, "cvName": file.filename, "filePath": path, "fileSize": os.path.getsize(path), "mimeType": file.content_type, "isPrimary": 0, "uploadedAt": uploaded_at}
        cv_id = addCV(conn, cv_data)
        if not cv_id: raise HTTPException(status_code=500, detail="Failed to upload CV")
        return CVUploadOut(cvId=cv_id, cvName=str(file.filename), filePath=path, uploadedAt=uploaded_at)
    finally:
        conn.close()

@app.delete(
    "/v1/workwise/cvs/{user_id}/{cv_id}",
    response_model=ApiResponse, # <-- Use generic response
    tags=["cv"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("DELETE", "/v1/workwise/cvs")]))]
)
def removeCV(user_id: int, cv_id: int):
    conn = getDatabase()
    try:
        if deleteCV(conn, cv_id, user_id):
            return ApiResponse(message="CV deleted successfully")
        else:
            raise HTTPException(status_code=404, detail="CV not found")
    finally:
        conn.close()

@app.put(
    "/v1/workwise/cvs/{user_id}/primary/{cv_id}",
    response_model=ApiResponse, # <-- Use generic response
    tags=["cv"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("PUT", "/v1/workwise/cvs/primary")]))]
)
def makePrimaryCV(user_id: int, cv_id: int):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        if setPrimaryCV(conn, cv_id, user_id):
            return ApiResponse(message="CV set as primary")
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
def route_list_user_qualifications(user_id: int):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        quals = getUserQualifications(conn, user_id)
        return [QualificationOut(**q) for q in quals]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/qualifications/{user_id}",
    response_model=QualificationOut,
    tags=["qualifications"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/qualifications")]))]
)
def addUserQualification(user_id: int, body: QualificationIn):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user: raise HTTPException(status_code=404, detail="User not found")
        qual_data: dict[str, Any] = body.model_dump()
        qual_data["userId"] = user_id
        qual_data["endDate"] = body.endDate if not body.isCurrent else None
        qual_data["isCurrent"] = int(body.isCurrent)
        qual_data["createdAt"] = datetime.now(timezone.utc).isoformat()
        qual_id = addQualification(conn, qual_data)
        if not qual_id: raise HTTPException(status_code=500, detail="Failed to add qualification")
        return QualificationOut(qualificationId=qual_id, **qual_data)
    finally:
        conn.close()

@app.put(
    "/v1/workwise/qualifications/{user_id}/{qualification_id}",
    response_model=QualificationOut,
    tags=["qualifications"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("PUT", "/v1/workwise/qualifications")]))]
)
def updateUserQualification(user_id: int, qualification_id: int, body: QualificationUpdateIn):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        updates: dict[str, Any] = body.model_dump(exclude_unset=True)
        if updates:
            if "isCurrent" in updates: updates["isCurrent"] = int(updates["isCurrent"])
            if not updateQualification(conn, qualification_id, user_id, updates):
                raise HTTPException(status_code=404, detail="Qualification not found or update failed")
        quals = getUserQualifications(conn, user_id)
        updated_qual = next((q for q in quals if q["qualificationId"] == qualification_id), None)
        if updated_qual: return QualificationOut(**updated_qual)
        else: raise HTTPException(status_code=404, detail="Qualification not found after update")
    finally:
        conn.close()

@app.delete(
    "/v1/workwise/qualifications/{user_id}/{qualification_id}",
    response_model=ApiResponse, # <-- Use generic response
    tags=["qualifications"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("DELETE", "/v1/workwise/qualifications")]))]
)
def removeUserQualification(user_id: int, qualification_id: int):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        if deleteQualification(conn, qualification_id, user_id):
            return ApiResponse(message="Qualification deleted successfully")
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
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user: raise HTTPException(status_code=404, detail="User not found")
        apps_count = getUserApplicationsCount(conn, user_id)
        saved_count = getUserSavedJobsCount(conn, user_id)
        return UserStatsOut(applicationsCount=apps_count, savedJobsCount=saved_count)
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
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        jobs = getSavedJobs(conn, user_id)
        return [SavedJobOut(**job) for job in jobs]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/saved-jobs/{user_id}",
    response_model=SavedJobOut,
    tags=["saved_jobs"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/saved-jobs")]))]
)
def saveJob(user_id: int, body: SavedJobIn):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        user = getUserById(conn, user_id)
        if not user: raise HTTPException(status_code=404, detail="User not found")
        saved_at = datetime.now(timezone.utc).isoformat()
        job_data: dict[str, Any] = body.model_dump()
        job_data['userId'] = user_id
        job_data['savedAt'] = saved_at
        job_id = addSavedJob(conn, job_data)
        if not job_id: raise HTTPException(status_code=500, detail="Failed to save job")
        return SavedJobOut(savedJobId=job_id, **job_data)
    finally:
        conn.close()

@app.delete(
    "/v1/workwise/saved-jobs/{user_id}/{saved_job_id}",
    response_model=ApiResponse, # <-- Use generic response
    tags=["saved_jobs"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("DELETE", "/v1/workwise/saved-jobs")]))]
)
def removeSavedJob(user_id: int, saved_job_id: int):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        if deleteSavedJob(conn, saved_job_id, user_id):
            return ApiResponse(message="Saved job deleted successfully")
        else:
            raise HTTPException(status_code=404, detail="Saved job not found")
    finally:
        conn.close()

# ========== BUSINESS & JOB ENDPOINTS ==========
@app.post(
    "/v1/workwise/businesses",
    response_model=BusinessOut,
    tags=["businesses"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/businesses")]))]
)
def create_business(body: BusinessIn):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        created_at = datetime.now(timezone.utc).isoformat()
        biz_data = body.model_dump()
        biz_data["createdAt"] = created_at
        biz_id = addBusiness(conn, biz_data)
        if not biz_id: raise HTTPException(status_code=500, detail="Failed to create business")
        return BusinessOut(businessId=biz_id, createdAt=created_at, **body.model_dump())
    finally:
        conn.close()

@app.post(
    "/v1/workwise/jobs",
    response_model=JobOut,
    tags=["jobs"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/jobs")]))]
)
def create_job(body: JobIn):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        date_posted = datetime.now(timezone.utc).isoformat()
        job_data = body.model_dump() 
        job_data["datePosted"] = date_posted
        job_data["isActive"] = True
        job_id = addJob(conn, job_data)
        if not job_id: raise HTTPException(status_code=500, detail="Failed to create job")
        return JobOut(jobId=job_id, datePosted=date_posted, isActive=True, **body.model_dump())
    finally:
        conn.close()

@app.get(
    "/v1/workwise/jobs",
    response_model=List[JobListingOut],
    tags=["jobs"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/jobs")]))]
)
def list_active_jobs(limit: int = 20, offset: int = 0):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        jobs = getActiveJobs(conn, limit, offset)
        return [JobListingOut(**job) for job in jobs]
    finally:
        conn.close()

@app.get(
    "/v1/workwise/jobs/detail/{job_id}",
    response_model=JobDetailOut,
    tags=["jobs"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/jobs/detail")]))]
)
def get_job_details(job_id: int):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        job = getJobById(conn, job_id)
        if not job: raise HTTPException(status_code=404, detail="Job not found")
        return JobDetailOut(**job)
    finally:
        conn.close()

@app.get(
    "/v1/workwise/jobs/search",
    response_model=List[JobListingOut],
    tags=["jobs"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/jobs/search")]))]
)
def search_jobs_endpoint(
    query: Optional[str] = None,
    employment_type: Optional[str] = None,
    work_arrangement: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    conn = getDatabase()
    try:
        jobs = searchJobs(conn, query, employment_type, work_arrangement, location, limit, offset)
        return [JobListingOut(**job) for job in jobs]
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
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        unions = getUnions(conn)
        return [UnionOut(unionId=union["union_id"], register_num=union["register_num"], sector_info=union["sector_info"], membership_size=union["membership_size"], is_active_council=bool(union["is_active_council"]), createdAt=union["created_at"]) for union in unions]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/unions",
    response_model=UnionOut,
    tags=["unions"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/unions")]))]
)
def createUnion(body: UnionIn):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        if unionExists(conn, body.register_num):
            raise HTTPException(status_code=409, detail="Union registration number already exists")
        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute("INSERT INTO unions (register_num, sector_info, membership_size, is_active_council, created_at) VALUES (?, ?, ?, ?, ?)", (body.register_num, body.sector_info, body.membership_size, int(body.is_active_council), created_at))
        conn.commit()
        union_id = cur.lastrowid
        if union_id is None: raise HTTPException(status_code=500, detail="Failed to create union")
        return UnionOut(unionId=union_id, register_num=body.register_num, sector_info=body.sector_info, membership_size=body.membership_size, is_active_council=body.is_active_council, createdAt=created_at)
    finally:
        conn.close()

@app.get(
    "/v1/workwise/union_members",
    response_model=List[UnionMemberOut],
    tags=["union_members"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/union_members")]))]
)
def listUnionMembers(union_id: Optional[int] = None):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        members = getUnionMembers(conn, union_id)
        return [UnionMemberOut(membershipId=member["membership_id"], worker_id=member["worker_id"], union_id=member["union_id"], membership_num=member["membership_num"], status=member["status"]) for member in members]
    finally:
        conn.close()

@app.post(
    "/v1/workwise/union_members",
    response_model=UnionMemberOut,
    tags=["union_members"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/union_members")]))]
)
def addMemberToUnion(body: UnionMemberIn):
    # ... (unchanged) ...
    conn = getDatabase()
    try:
        if workerInUnion(conn, body.worker_id, body.union_id):
            raise HTTPException(status_code=409, detail="Worker is already a member of this union")
        membership_num = body.membership_num or f"MEM-{body.worker_id}-{body.union_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        cur = conn.cursor()
        cur.execute("INSERT INTO union_members (worker_id, union_id, membership_num, status) VALUES (?, ?, ?, ?)", (body.worker_id, body.union_id, membership_num, body.status or "active"))
        conn.commit()
        membership_id = cur.lastrowid
        if membership_id is None: raise HTTPException(status_code=500, detail="Failed to add union member")
        cur.execute("UPDATE unions SET membership_size = membership_size + 1 WHERE union_id = ?", (body.union_id,))
        conn.commit()
        return UnionMemberOut(membershipId=membership_id, worker_id=body.worker_id, union_id=body.union_id, membership_num=membership_num, status=body.status or "active")
    finally:
        conn.close()