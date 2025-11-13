from pydantic import BaseModel, EmailStr
from typing import Optional

# ========== AUTH MODELS ==========
class RegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str

class RegisterOut(BaseModel):
    userId: int
    username: str
    email: EmailStr
    role: str
    createdAt: str
    isActive: bool

class LoginIn(BaseModel):
    usernameOrEmail: str
    password: str

class LoginOut(BaseModel):
    userId: int
    username: str
    email: EmailStr
    role: str

# ========== PROFILE MODELS ==========
class UserProfileOut(BaseModel):
    userId: int
    username: str
    email: EmailStr
    role: str
    profileImage: Optional[str] = None
    profileName: Optional[str] = None
    profileBio: Optional[str] = None
    phoneNumber: Optional[str] = None
    location: Optional[str] = None
    sideProjects: Optional[str] = None  # Added for synchronization
    createdAt: str
    updatedAt: Optional[str] = None

class UserProfileUpdateIn(BaseModel):
    profileName: Optional[str] = None
    profileBio: Optional[str] = None
    phoneNumber: Optional[str] = None
    location: Optional[str] = None
    sideProjects: Optional[str] = None  # Added for synchronization

class ProfileImageUploadOut(BaseModel):
    userId: int
    profileImage: str
    message: str

# ========== CV MODELS ==========
class CVOut(BaseModel):
    cvId: int
    # Removed duplicate cvId field
    userId: int
    cvName: str
    filePath: str
    fileSize: Optional[int] = None
    mimeType: Optional[str] = None
    isPrimary: bool
    uploadedAt: str

class CVUploadOut(BaseModel):
    cvId: int
    cvName: str
    filePath: str
    uploadedAt: str

# ========== QUALIFICATION MODELS ==========
class QualificationIn(BaseModel):
    qualificationType: str  # e.g., "Matric", "Diploma", "Degree", "Certificate"
    institution: str
    fieldOfStudy: Optional[str] = None
    qualificationName: str
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    isCurrent: bool = False
    gradeOrGpa: Optional[str] = None
    description: Optional[str] = None

class QualificationOut(QualificationIn):
    qualificationId: int
    userId: int
    createdAt: str

class QualificationUpdateIn(BaseModel):
    qualificationType: Optional[str] = None
    institution: Optional[str] = None
    fieldOfStudy: Optional[str] = None
    qualificationName: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    isCurrent: Optional[bool] = None
    gradeOrGpa: Optional[str] = None
    description: Optional[str] = None

# ========== STATS MODELS ==========
class UserStatsOut(BaseModel):
    applicationsCount: int
    savedJobsCount: int

# ========== SAVED JOBS MODELS ==========
class SavedJobIn(BaseModel):
    jobTitle: str
    companyName: str
    jobLocation: Optional[str] = None
    salaryRange: Optional[str] = None
    jobDescription: Optional[str] = None

class SavedJobOut(SavedJobIn):
    savedJobId: int
    userId: int
    savedAt: str

# ========== UNION MODELS ==========
class UnionIn(BaseModel):
    register_num: str
    sector_info: str
    membership_size: int = 0
    is_active_council: bool = False

class UnionOut(UnionIn):
    unionId: int
    createdAt: str

class UnionMemberIn(BaseModel):
    worker_id: int
    union_id: int
    membership_num: Optional[str] = None
    status: Optional[str] = "active"

class UnionMemberOut(UnionMemberIn):
    membershipId: int