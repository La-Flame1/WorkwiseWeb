from pydantic import BaseModel, EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until expire

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None

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
    status: Optional[str] = "active"  # e.g., "active", "inactive"

class UnionMemberOut(UnionMemberIn):
    membershipId: int

class WorkerIn(BaseModel):
    phone: Optional[str] = None
    bio: Optional[str] = None
    experience_years: Optional[int] = 0
    availability_status: Optional[str] = "available"

class WorkerOut(WorkerIn):
    workerId: int
    userId: int
    createdAt: str
    updatedAt: str

class EmployerIn(BaseModel):
    company_name: str
    location: Optional[str] = None
    industry: Optional[str] = None

class EmployerOut(EmployerIn):
    employerId: int
    userId: int
    createdAt: str

# Jobs
class JobIn(BaseModel):
    title: str
    description: str
    salary_range: Optional[float] = None
    required_skills: Optional[str] = None  # Comma-separated or JSON
    compliance_required: Optional[bool] = False
    deadline: Optional[str] = None  # ISO date

class JobOut(JobIn):
    jobId: int
    employerId: int
    postedAt: str
    status: str = "open"

# Applications
class ApplicationIn(BaseModel):
    job_id: int
    cover_letter: Optional[str] = None

class ApplicationOut(ApplicationIn):
    applicationId: int
    workerId: int
    appliedAt: str
    matchScore: float = 0.0
    status: str = "pending"

# Courses
class CourseIn(BaseModel):
    title: str
    description: str
    provider: Optional[str] = None
    duration_hours: Optional[int] = 0
    cost: Optional[float] = 0.0
    skills_covered: Optional[str] = None  # Comma-separated
    certification_available: Optional[bool] = False

class CourseOut(CourseIn):
    courseId: int
    status: str = "available"
    createdAt: str

# Worker_Courses (enrollments)
class WorkerCourseIn(BaseModel):
    course_id: int
    enrollment_date: Optional[str] = None

class WorkerCourseOut(WorkerCourseIn):
    enrollmentId: int
    workerId: int
    completionStatus: str = "enrolled"
    completionPercentage: float = 0.0
    certificateEarned: bool = False
# Government
class GovernmentIn(BaseModel):
    department_name: str
    contact_info: str
    regulatory_focus: str

class GovernmentOut(GovernmentIn):
    governmentId: int
    createdAt: str
    updatedAt: str

# Government Programs
class GovernmentProgramIn(BaseModel):
    government_id: int
    program_name: str
    eligibility_criteria: str
    skills_focus: str
    is_active: Optional[bool] = True

class GovernmentProgramOut(GovernmentProgramIn):
    programId: int
    createdAt: str

# Training Institutions
class TrainingInstitutionIn(BaseModel):
    name: str
    location: str
    contact_info: str
    accreditation_status: Optional[str] = "pending"

class TrainingInstitutionOut(TrainingInstitutionIn):
    institutionId: int
    isActive: bool = True
    createdAt: str