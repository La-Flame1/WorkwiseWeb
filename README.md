# Workwise API

[![FastAPI](https://img.shields.io/badge/FastAPI-1.0-blue?logo=fastapi)](https://fastapi.tiangolo.com/) [![SQLite](https://img.shields.io/badge/Database-SQLite-green?logo=sqlite)](https://www.sqlite.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview
Workwise API is a robust, scalable backend service built with **FastAPI** for a labor management platform. It supports worker-employer matching, union management, job applications, skills training via courses, and government program integration. The API handles user authentication, data persistence with SQLite, and secure token-based access control. Designed for a mobile/web app ecosystem, it emphasizes intuitive CRUD operations, validation, and real-time testing via interactive docs.

Key goals:
- Streamline job postings and applications with AI-like match scoring.
- Manage unions and memberships for labor organization.
- Track worker skills through courses and certifications.
- Integrate government programs for eligibility and regulatory compliance.
- Support training institutions for accredited learning paths.

This project serves as the core API layer, with endpoints grouped by feature (e.g., auth, jobs, unions) for easy extension.

## Features
- **User Authentication**: Secure registration/login with Argon2 password hashing (passlib).
- **Profile Management**: Workers and employers extend base users with bios, experience, and company details.
- **Job Marketplace**: Post, list, and apply for jobs with salary ranges, skills matching, and status tracking.
- **Union System**: Create/list unions and manage memberships with size auto-updates.
- **Skills & Training**: Enroll workers in courses, track progress, and link to certifications.
- **Government Integration**: Departments and programs with eligibility criteria and skills focus.
- **API Security**: Custom endpoint tokens (`X-Endpoint-Token`) for protected routes.
- **Validation & Errors**: Pydantic models ensure data integrity; custom 401/409/422 handlers.
- **Docs & Testing**: Auto-generated Swagger UI (`/docs`) and ReDoc (`/redoc`); supports cURL/Python testing.
- **Database**: SQLite with WAL mode for concurrency; schemas include FKs and indexes.

## Quick Start
### Prerequisites
- Python 3.8+.
- Git.

### Setup
1. **Clone the Repo**:
   ```
   git clone https://github.com/La-Flame1/WorkwiseWeb.git
   cd WorkwiseWeb
   ```

2. **Create Virtual Environment**:
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # Windows PowerShell
   # On macOS/Linux: source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```
   pip install fastapi uvicorn[standard] pydantic[email] passlib[argon2] jinja2 requests python-jose[cryptography]
   # Or: pip install -r requirements.txt (if available)
   ```

4. **Run the Server**:
   ```
   cd Src  # Navigate to folder with main.py
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   - Access at http://localhost:8000/docs (Swagger UI).
   - Database auto-initializes (`databaseWorkwise.db` in root).

5. **Test Endpoints**:
   - Ping: `GET /v1/ping` (no token needed).
   - Register: `POST /v1/workwise/account` (token: `USNACCTOK123`, body: `{"username": "test", "email": "test@example.com", "password": "pass123"}`).
   - Create Union: `POST /v1/workwise/unions` (token: `UNIONCREATETOK789`, body as in docs).

### Development Notes
- **Tokens**: Hardcoded in `main.py`—use Swagger's "Authorize" for easy input.
- **DB Location**: `databaseWorkwise.db` in root; edit `db.py` for path.
- **Offline Testing**: Use cURL or Python requests for API calls.

## Project Structure
```
WorkwiseWeb/
├── Src/
│   ├── main.py              # FastAPI app, routes, auth
│   ├── Models/
│   │   └── models.py        # Pydantic schemas (In/Out models)
│   └── Database/
│       └── db.py            # SQLite connections, CRUD functions
├── Templates/               # Jinja2 for error pages (e.g., 401.html)
├── databaseWorkwise.db      # Auto-generated SQLite DB
├── requirements.txt         # Dependencies (optional)
├── .gitignore               # Ignore venv, .db-wal, etc.
└── README.md                # This file
```

## API Endpoints
All protected routes require `X-Endpoint-Token` header. Use Swagger for full schemas/examples.

| Tag | Method | Path | Description | Token |
|-----|--------|------|-------------|-------|
| auth | POST | /v1/workwise/account | Register user | USNACCTOK123 |
| auth | POST | /v1/workwise/user | Login user | USNDPNQNKW |
| unions | POST | /v1/workwise/unions | Create union | UNIONCREATETOK789 |
| unions | GET | /v1/workwise/unions | List unions | UNIONLISTTOK456 |
| union_members | POST | /v1/workwise/union_members | Add member | MEMBERADDTOK345 |
| union_members | GET | /v1/workwise/union_members | List members (?union_id=1) | MEMBERLISTTOK012 |
| workers | POST | /v1/workwise/workers | Create worker profile | WORKERCREATETOK999 |
| workers | GET | /v1/workwise/workers | List workers | WORKERLISTTOK888 |
| employers | POST | /v1/workwise/employers | Create employer profile | EMPLOYERCREATETOK777 |
| employers | GET | /v1/workwise/employers | List employers | EMPLOYERLISTTOK666 |
| jobs | POST | /v1/workwise/jobs | Post job | JOBCREATETOK555 |
| jobs | GET | /v1/workwise/jobs | List jobs (?employer_id=1) | JOBLISTTOK444 |
| applications | POST | /v1/workwise/applications | Apply to job | APPCREATETOK333 |
| applications | GET | /v1/workwise/applications | List apps (?worker_id=1 or ?job_id=1) | APPLISTTOK222 |
| courses | POST | /v1/workwise/courses | Create course | COURSECREATETOK111 |
| courses | GET | /v1/workwise/courses | List courses | COURSELISTTOK000 |
| worker_courses | POST | /v1/workwise/worker_courses | Enroll worker | ENROLLTOK999 |
| worker_courses | GET | /v1/workwise/worker_courses | List enrollments (?worker_id=1) | ENROLLLISTTOK888 |
| governments | POST | /v1/workwise/governments | Create department | GOVCREATETOK101 |
| governments | GET | /v1/workwise/governments | List departments | GOVLISTTOK102 |
| government_programs | POST | /v1/workwise/government_programs | Create program | PROGCREATETOK103 |
| government_programs | GET | /v1/workwise/government_programs | List programs (?government_id=1) | PROGLISTTOK104 |
| training_institutions | POST | /v1/workwise/training_institutions | Create institution | INSTCREATETOK105 |
| training_institutions | GET | /v1/workwise/training_institutions | List institutions | INSTLISTTOK106 |

## Database Schema
SQLite-based (`databaseWorkwise.db`):
- **users**: Core auth (user_id, username, email, etc.).
- **workers/employers**: Profiles (FK to users).
- **jobs**: Postings (FK to employers).
- **applications**: Matches (FK to jobs/workers, match_score).
- **courses**: Training (title, cost, skills).
- **worker_courses**: Enrollments (FK to workers/courses, progress).
- **unions/union_members**: Labor groups (from initial features).
- **governments/government_programs**: Regulatory (FK between them).
- **training_institutions**: Accredited providers.

Schemas include indexes/FKs for performance/integrity.







