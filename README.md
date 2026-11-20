# Student Portal API

FastAPI, SQLAlchemy, SQLite, React, and Vite student-request portal.

## Backend setup (Windows PowerShell)

```powershell
cd C:\Users\yugen\Downloads\portal-api\portal-api
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend is available at http://127.0.0.1:8000 and Swagger UI at http://127.0.0.1:8000/docs.

## Frontend setup

In a second terminal:

```powershell
cd C:\Users\yugen\Downloads\portal-api\portal-api\frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5173/. Vite proxies `/api` to the FastAPI server.

## Demo accounts

- Student: `student@example.com` / `Student@12345`
- Admin: `admin@example.com` / `Admin@12345`

## Configuration

The project is configured with SQLite through `.env`:

```text
DATABASE_URL=sqlite:///./portal.db
JWT_SECRET=your-long-random-secret
COOKIE_SECURE=false
UPLOAD_DIR=uploads
SEED_ADMIN_PASSWORD=Admin@12345
SEED_STUDENT_PASSWORD=Student@12345
```

The `.env.example` file contains a safe local template. PostgreSQL remains optional: add `DB_PASSWORD` and switch `DATABASE_URL` to a PostgreSQL URL before running Docker Compose.
