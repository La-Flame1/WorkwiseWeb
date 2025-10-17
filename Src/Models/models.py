from pydantic import BaseModel, EmailStr

# -------- Register --------
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

# -------- Login --------
class LoginIn(BaseModel):
    usernameOrEmail: str
    password: str

class LoginOut(BaseModel):
    userId: int
    username: str
    email: EmailStr
    role: str
