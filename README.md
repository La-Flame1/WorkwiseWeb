# WorkwiseWeb
[![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/Nevvyboi/WorkwiseWeb)

WorkwiseWeb is the backend API for a professional networking and job-seeking application. Built with FastAPI, it provides a comprehensive set of features for user management, profile customization, job searching, and union membership tracking. The API is designed to be robust and scalable, utilizing a SQLite database for data persistence and Argon2 for secure password hashing.

## Features

*   **Secure Authentication**: User registration, login, and password reset functionality using email verification codes. Passwords are securely hashed with Argon2.
*   **User Profile Management**: Full CRUD capabilities for user profiles, including personal details, bio, contact information, and location.
*   **File Uploads**: Supports uploading and managing user profile images and CVs (PDF, DOC, DOCX). Files are stored on the server's filesystem.
*   **CV & Qualification Management**: Users can upload multiple CVs, set a primary one, and manage their educational and professional qualifications.
*   **Job & Application Tracking**: View job listings, save interesting jobs, and track statistics like the number of saved jobs and applications.
*   **Union & Membership Management**: Functionality to create and list trade unions, as well as manage worker memberships within those unions.
*   **Token-Based API Security**: Endpoints are protected using a static token-based authentication via the `X-Endpoint-Token` header.

## Technology Stack

*   **Backend**: Python, FastAPI
*   **Web Server**: Uvicorn
*   **Database**: SQLite
*   **Password Hashing**: Argon2 (`passlib`)
*   **Data Validation**: Pydantic
*   **Dependencies**: `python-multipart`, `jinja2`

## Getting Started

Follow these instructions to get a local copy up and running for development and testing purposes.

### Prerequisites

*   Python 3.8+
*   A virtual environment tool (e.g., `venv`)

### Installation & Running

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/nevvyboi/workwiseweb.git
    cd workwiseweb/Src
    ```

2.  **Create and activate a virtual environment:**
    *   On macOS/Linux:
        ```sh
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   On Windows:
        ```sh
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Install the required dependencies:**
    The project contains two `requirements.txt` files. Use the one located in the nested `Src` directory as it contains all necessary packages for the full feature set.
    ```sh
    pip install -r Src/requirements.txt
    ```

4.  **Configure Email Settings (Optional):**
    For the password reset functionality to work, you must configure your SMTP email settings in `Src/Src/Utils/emailUtil.py`.
    ```python
    # Src/Src/Utils/emailUtil.py
    
    SMTP_SERVER = "smtp.example.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "your-email@example.com"
    SENDER_PASSWORD = "your-app-password" 
    ```

5.  **Run the application:**
    From the `Src` directory, run the FastAPI application using Uvicorn.
    ```sh
    uvicorn Src.main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`. You can access the interactive API documentation at `http://127.0.0.1:8000/docs`.

## API Usage

All API endpoints are protected and require an `X-Endpoint-Token` header for authentication. The tokens are hardcoded in `Src/Src/main.py`.

### Example: Register a New User

To register a new user, you need to use the token associated with the `/v1/workwise/account` endpoint.

*   **Endpoint**: `POST /v1/workwise/account`
*   **Token**: `USNACCTOK123`

You can make a request using cURL:
```sh
curl -X POST "http://127.0.0.1:8000/v1/workwise/account" \
-H "Content-Type: application/json" \
-H "X-Endpoint-Token: USNACCTOK123" \
-d '{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "a-strong-password"
}'
```

### Main Endpoint Categories

The API is organized into the following categories, visible in the `/docs`:

*   **auth**: User registration, login, and password management.
*   **profile**: CRUD for user profiles and image uploads.
*   **cv**: CV listing, uploading, and management.
*   **qualifications**: CRUD for user qualifications.
*   **stats**: User activity statistics.
*   **saved_jobs**: Saving and managing jobs.
*   **jobs**: Public endpoints for listing and viewing jobs.
*   **unions**: Creating and listing trade unions.
*   **union\_members**: Managing memberships in unions.

## Database

The application uses SQLite as its database. The database file, `databaseWorkwise.db`, is automatically created in the `Src/` directory upon the first run of the application. The necessary tables are also created and initialized by `Database/db.py`.

The database schema includes tables for:
*   `users`
*   `cvs`
*   `qualifications`
*   `job_applications`
*   `saved_jobs`
*   `jobs`
*   `unions`
*   `union_members`
*   `password_reset_tokens`

## License

This project is released into the public domain under The Unlicense. See the `LICENSE` file for more details.
