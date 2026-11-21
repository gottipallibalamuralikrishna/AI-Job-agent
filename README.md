# JobPilot AI

JobPilot is a job search workspace that matches openings against a resume, tracks applications, and helps you contact recruiters. The frontend uses React, TypeScript, Vite, and Material UI. The backend uses FastAPI, SQLAlchemy, Alembic, and PostgreSQL.

## 1. Install prerequisites

- Python 3.12 is recommended. The backend container uses Python 3.12.
- Node.js 22 and npm are recommended. The staging frontend image uses Node.js 22.
- PostgreSQL 16 is the version used in staging. For local development, use an existing PostgreSQL server or run one with Docker.
- A Gemini API key is needed for AI resume profile extraction. Telegram and Gmail credentials are needed only for those integrations.

Run the following commands from the repository root on Windows PowerShell unless otherwise indicated.

## 2. Set up PostgreSQL

Create a database and database user, or use your existing local database. If you need a fresh local database and have Docker running, this command creates a PostgreSQL container with a persistent volume and binds its port to loopback. If port 5432 is already in use, use the existing database or change the host port and update your database URL.

```powershell
docker run --name jobpilot-db -e POSTGRES_DB=jobpilot -e POSTGRES_USER=jobpilot -e POSTGRES_PASSWORD=jobpilot -p 127.0.0.1:5432:5432 -v jobpilot-local-data:/var/lib/postgresql/data -d postgres:16
```

Those credentials are for local development only. On subsequent runs, start the existing container with `docker start jobpilot-db`.

## 3. Install backend dependencies and configure the app

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item ..\.env.example .env }
```

Use an existing virtual environment if it already has your dependencies installed. If you use a system Python launcher other than `py`, run `python -m venv venv` with your chosen Python interpreter.

Open `backend/.env` and set values for your local setup. The sample database host is `db` for containers. Use `127.0.0.1` when you run FastAPI directly on your machine.

```dotenv
DATABASE_URL=postgresql+psycopg://jobpilot:jobpilot@127.0.0.1:5432/jobpilot
SECRET_KEY=replace-this-with-a-random-signing-secret
FRONTEND_ORIGIN=http://127.0.0.1:5173
COOKIE_SECURE=false
GEMINI_API_KEY=
COLLECTION_ENABLED=true
COLLECTION_TIMEZONE=Asia/Kolkata
OUTREACH_ENABLED=false
```

Generate a signing secret with `.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"` and store it in `backend/.env`. Keep the file and all real credentials private. On Linux or macOS, replace `py -3.12` with `python3.12` and `.\venv\Scripts\python.exe` with `./venv/bin/python`.

## 4. Apply migrations and start the backend

In the backend terminal, wait for PostgreSQL to accept connections, then run:

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- [Backend health check](http://127.0.0.1:8000/health)
- [API documentation](http://127.0.0.1:8000/docs)

Keep the terminal running. After pulling a change with migrations, run `alembic upgrade head` before restarting the backend.

## 5. Install frontend dependencies and start Vite

In a second terminal, from the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open [JobPilot locally](http://127.0.0.1:5173). The public landing page links to registration and sign-in. The Vite server forwards `/api/v1` to the backend on port 8000. Leave `VITE_API_URL` unset for this setup and use the same frontend hostname each time so the browser can reuse its session cookie.

Stop the development servers with **Ctrl+C** in their terminals.

## 6. Use the app

1. Sign in and open **Resume Profile**. Upload a PDF or DOCX up to 5 MB. Set the resume as primary and choose **Extract Profile**.
2. After extraction, JobPilot queues collection for your primary resume. Choose **Collect matching jobs** to start a run manually. Review the current run and its progress under **Resume Profile** or open the collection summary in **AI Matches**.
3. JobPilot saves eligible matches scoring **strictly above 80%**. Keyword-based sources can search related roles from the resume title, experience, and skills. JobPilot merges duplicate postings and applies the account's location preferences. Overseas remote roles must explicitly allow applicants from the preferred country or worldwide when international remote matching is enabled.
4. Choose **Mark as applied** to move a job out of **AI Matches** and into the **Applications** table.

Scheduled collection runs at **8:00 AM IST** while the backend is running. If the backend becomes available later that day, it can catch up. Host the backend on a server that stays running if you need collection while your laptop is off. The default retention is 30 days for collected jobs and matches. HR contacts and application history are retained.

## 7. Configure job sources and Telegram

JobPilot supports Greenhouse, Lever, RSS, public career pages with structured job data, Himalayas, and configured Telegram channels. Manage sources through the API documentation under **Job Sources**. Disabled sources are skipped. Public job-board pages vary in what they expose and may require an official feed or API.

For Telegram, add `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` to `backend/.env`. From the backend folder, authorize the session interactively on the machine that will run collection:

```powershell
.\venv\Scripts\python.exe -m app.collectors.telegram --login
```

Add the public channel URL as a Telegram job source if it is missing. Keep the generated files in `backend/telegram_sessions/` private. `TELEGRAM_LOOKBACK_HOURS` defaults to 24. Telegram jobs use the same location and score checks as the other sources.

## 8. Configure recruiter email

Open **HR Contacts → Email imported recruiters**, or choose **Email recruiter** from a contact's details. Enable the sending worker with `OUTREACH_ENABLED=true` and restart the backend. Connect a personal Gmail account using an app password, which requires Google 2-Step Verification.

Create a template in the app or upload a UTF-8 `.txt` or `.json` file up to 128 KB. Text files start with `Subject: Your subject` followed by the message body. JSON files contain `name`, `subject`, and `body`. Templates support `{recruiter_name}`, `{company}`, and `{sender_name}`.

Select recruiter contacts or enter email addresses manually. Choose whether to attach your primary resume and preview the message before sending. The backend sends individual emails through its queue. Defaults are 100 attempts per rolling 24 hours and 10 seconds between attempts. Preserve the private mail encryption key across deployments if you want to retain an existing Gmail connection.

## 9. Run development checks

From `backend/`:

```powershell
.\venv\Scripts\python.exe -m pytest tests -q
# Include database integration tests using isolated schemas.
$env:TEST_POSTGRES = '1'
.\venv\Scripts\python.exe -m pytest tests -q
```

From `frontend/`:

```powershell
npm run build
npm run preview
```

The preview server prints its URL. Keep the backend running if you want the preview to load live data.

## 10. Deploy private staging

Follow [the staging guide](STAGING.md) for the Docker Compose setup. It serves the frontend and `/api/v1` on one HTTPS domain and restricts access to a trusted IP or network. It keeps PostgreSQL and private uploads in persistent volumes. Collection and outreach are disabled initially in staging so you can verify the data, credentials, and session before turning the workers on.

Use a clean source bundle for deployment. Keep live environment files, resumes, Telegram sessions, database backups, and mail keys outside Git. If Telegram session files were shared through old Git history, revoke the old session and authorize a fresh one. The current HR directory is shared among signed-in users on the same database, so review access before opening registration publicly.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Backend cannot connect to PostgreSQL | Check that PostgreSQL is running and that the host, port, credentials, and database match `backend/.env`. |
| Frontend cannot load data or sign in | Open the backend health check, verify port 8000, and keep the frontend on a consistent hostname. If needed, sign in again after changing hosts or rotating the signing secret. |
| Resume uploads but profile extraction fails | Verify that the document has readable text and that the Gemini API key is configured. If Gemini is temporarily unavailable, retry extraction once the service recovers. |
| Job collection does not begin | Confirm the backend worker is enabled, the primary resume has an extracted profile, and active sources are configured. |
| Telegram source fails | Verify the server's Telegram credentials, session authorization, and access to the configured channel. |
| No new matches appear | Check the collection summary. A completed run can return zero eligible posts above the score cutoff. |
