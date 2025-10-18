from datetime import datetime
from typing import Optional, Callable

from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exception_handlers import http_exception_handler as defaultHttpHandler
from passlib.context import CryptContext

from Models.models import RegisterIn, RegisterOut, LoginIn, LoginOut

from Database.db import initDatabase, getDatabase, userExists, getUsersDetails

app = FastAPI(title = "Workwise API", version = "1.0")
templates = Jinja2Templates(directory = "Templates")

endpointTokens = {
    "POST:/v1/workwise/account": "USNACCTOK123",
    "POST:/v1/workwise/user": "USNDPNQNKW",
}

# uvicorn main:app --reload --host 0.0.0.0 --port 8000

def key(method: str, path: str) -> str:
    return f"{method.upper()}:{path}"

def requireEndpointToken(expectedToken: str) -> Callable:
    async def checker(x_endpoint_token: Optional[str] = Header(default = None, alias = "X-Endpoint-Token")):
        if not x_endpoint_token or x_endpoint_token != expectedToken:
            raise HTTPException(status_code = 401, detail = "Missing or invalid endpoint token")
        return True
    return checker

pwd = CryptContext(schemes = ["argon2"], deprecated = "auto")

@app.on_event("startup")
def on_startup():
    initDatabase()

@app.exception_handler(HTTPException)
async def customHttpExceptionHandler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        accepts_html = "text/html" in request.headers.get("accept", "").lower()
        if accepts_html:
            return templates.TemplateResponse("401.html", {"request": request}, status_code = 401)
        return JSONResponse({"detail": exc.detail or "Unauthorized"}, status_code = 401)
    return await defaultHttpHandler(request, exc)

@app.get("/v1/ping")
def ping():
    return {"ok": True, "ts": datetime.utcnow().isoformat()}

@app.post(
    "/v1/workwise/account",
    response_model = RegisterOut,
    tags = ["auth"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/account")]))]
)
def register(body: RegisterIn):
    conn = getDatabase()
    try:
        if userExists(conn, body.username, body.email):
            raise HTTPException(status_code = 409, detail = "Username or email already exists")

        hashed = pwd.hash(body.password)
        created_at = datetime.utcnow().isoformat()

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, email, password_hash, role, created_at, is_active)
            VALUES (?, ?, ?, 'user', ?, 1)
        """, (body.username, body.email, hashed, created_at))
        conn.commit()

        user_id = cur.lastrowid
        return RegisterOut(
            userId = user_id,
            username = body.username,
            email = body.email,
            role = "user",
            createdAt = created_at,
            isActive = True
        )
    finally:
        conn.close()

@app.get("/v1/workwise/account", tags = ["auth"])
def registerProbeHtml():
    raise HTTPException(status_code = 401, detail = "Missing or invalid endpoint token")

@app.post(
    "/v1/workwise/user",
    response_model = LoginOut,
    tags = ["auth"],
    dependencies=[Depends(requireEndpointToken(endpointTokens[key("POST", "/v1/workwise/user")]))]
)
def login(body: LoginIn):
    conn = getDatabase()
    try:
        row = getUsersDetails(conn, body.usernameOrEmail)
        if not row or not pwd.verify(body.password, row["password_hash"]):
            raise HTTPException(status_code = 401, detail = "Invalid credentials")

        return LoginOut(
            userId = row["user_id"],
            username = row["username"],
            email = row["email"],
            role = row["role"]
        )
    finally:
        conn.close()

@app.get("/v1/workwise/user", tags = ["auth"])
def loginProbeHtml():
    raise HTTPException(status_code = 401, detail = "Missing or invalid endpoint token")
