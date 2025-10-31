from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security.api_key import APIKeyHeader
from fastapi.exception_handlers import http_exception_handler as defaultHttpHandler
from passlib.context import CryptContext
from Models.models import RegisterIn, RegisterOut, LoginIn, LoginOut, UnionIn, UnionOut, UnionMemberIn, UnionMemberOut

from Database.db import initDatabase, getDatabase, userExists, getUsersDetails, unionExists, getUnions, workerInUnion, getUnionMembers

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
        {"name": "union_members", "description": "Union membership management"}
    ],
    swagger_ui_default_parameters=[{"name": "X-Endpoint-Token", "in": "header", "required": True}]
)
templates = Jinja2Templates(directory="Templates")

endpoint_token = APIKeyHeader(name="X-Endpoint-Token")

endpointTokens = {
    "POST:/v1/workwise/account": "USNACCTOK123",
    "POST:/v1/workwise/user": "USNDPNQNKW",
    "GET:/v1/workwise/unions": "UNIONLISTTOK456",
    "POST:/v1/workwise/unions": "UNIONCREATETOK789",
    "GET:/v1/workwise/union_members": "MEMBERLISTTOK012",
    "POST:/v1/workwise/union_members": "MEMBERADDTOK345",
}

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
def loginProbeHtml() -> None:
    raise HTTPException(status_code=401, detail="Missing or invalid endpoint token")

# New routes for Unions (tagged "unions")
@app.get(
    "/v1/workwise/unions",
    response_model=List[UnionOut],
    tags=["unions"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/unions")]))]
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

# New routes for Union Members (tagged "union_members")
@app.get(
    "/v1/workwise/union_members",
    response_model=List[UnionMemberOut],
    tags=["union_members"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("GET", "/v1/workwise/union_members")]))]
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
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/union_members")]))]
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