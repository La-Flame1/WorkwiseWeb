from pydantic import BaseModel, EmailStr
from typing import Optional

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
