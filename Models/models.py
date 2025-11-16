from typing import List, Optional
from pydantic import BaseModel, EmailStr

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
    sideProjects: Optional[str] = None
    createdAt: str
    updatedAt: Optional[str] = None

class UserProfileUpdateIn(BaseModel):
    profileName: Optional[str] = None
    profileBio: Optional[str] = None
    phoneNumber: Optional[str] = None
    location: Optional[str] = None
    sideProjects: Optional[str] = None

class ProfileImageUploadOut(BaseModel):
    userId: int
    profileImage: str
    message: str

# ========== CV MODELS ==========
class CVOut(BaseModel):
    cvId: int
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
    qualificationType: str
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

# ========== BUSINESS & JOB MODELS ==========
class BusinessIn(BaseModel):
    name: str
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None

class BusinessOut(BusinessIn):
    businessId: int
    createdAt: str

class JobIn(BaseModel):
    businessId: int
    jobTitle: str
    description: str
    requirements: Optional[str] = None
    salaryRange: Optional[str] = None
    location: Optional[str] = None
    # --- START CHANGE ---
    employmentType: Optional[str] = None # e.g., "Full-time", "Contract"
    workArrangement: Optional[str] = None # e.g., "On-site", "Hybrid", "Remote"
    # --- END CHANGE ---

class JobOut(JobIn):
    jobId: int
    datePosted: str
    isActive: bool

class JobListingOut(BaseModel):
    """
    Combined model for displaying a job listing in the app.
    Includes job details and key business details.
    """
    jobId: int
    jobTitle: str
    description: str
    requirements: Optional[str] = None
    salaryRange: Optional[str] = None
    location: Optional[str] = None
    # --- START CHANGE ---
    employmentType: Optional[str] = None
    workArrangement: Optional[str] = None
    # --- END CHANGE ---
    datePosted: str
    businessId: int
    businessName: str
    businessAddress: Optional[str] = None
    businessWebsite: Optional[str] = None

class JobDetailOut(JobListingOut):
    """
    Extended model for the job detail screen.
    Includes full business details.
    """
    isActive: bool
    businessIndustry: Optional[str] = None
    businessDescription: Optional[str] = None


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

# ========== PASSWORD RESET MODELS ==========

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ForgotPasswordOut(BaseModel):
    message: str

class VerifyResetCodeIn(BaseModel):
    email: EmailStr
    code: str

class VerifyResetCodeOut(BaseModel):
    valid: bool
    message: str

class ResetPasswordIn(BaseModel):
    email: EmailStr
    code: str
    newPassword: str

class ResetPasswordOut(BaseModel):
    success: bool
    message: str

# A generic response model, useful for delete actions
class ApiResponse(BaseModel):
    message: str

# ========== SKILLS ASSESSMENT MODELS ==========
class SkillCategoryOut(BaseModel):
    skillName: str
    level: str
    score: int

class AssessmentHistoryOut(BaseModel):
    date: str
    category: str
    score: int

class ConversationCreateIn(BaseModel):
    participantIds: List[int]  

class ConversationOut(BaseModel):
    conversationId: int
    lastMessageAt: Optional[str] = None
    messageCount: int

class MessageSendIn(BaseModel):
    senderId: int
    body: str

class MessageOut(BaseModel):
    messageId: int
    conversationId: int
    senderId: int
    body: str
    createdAt: str