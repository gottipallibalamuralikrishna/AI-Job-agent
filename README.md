# JobPilot AI

Recruiter email is available in **HR Contacts → Email imported recruiters**, or **Email recruiter** in an individual email contact's details. Connect a personal Gmail account in the app with a Google app password (requires Google 2-Step Verification), edit the message, preview the recipients and primary-resume attachment, then click Send. The app's connection is independent of Gmail connected to Codex. App passwords are encrypted using a separate, automatically generated `private_storage/outreach/.mail-key`; preserve this directory across deployments. Alternatively supply a Fernet key through `OUTREACH_ENCRYPTION_KEY`. Use HTTPS when deployed. Changing or losing the mail key requires reconnecting the account; queued messages remain saved.

Before sending, create and save an email template or upload a UTF-8 `.txt` or `.json` template (maximum 128 KB), then select it in the email dialog. Text files begin with `Subject: Your subject` on the first line and the message body below. JSON files use `name`, `subject`, and `body`. **Download sample** provides a text template based on the primary resume. Plain-text messages support `{recruiter_name}`, `{company}`, and `{sender_name}`. Template edits must be saved and previewed again. Templates are private to each user; the selected template's name and content are retained with the campaign, so later template changes do not affect queued emails.

Under **Choose recipients**, search HR names, companies or emails and select contacts with checkboxes across pages. **Select this page**, **Clear selection**, and removable selection chips manage the selection. Alternatively choose **All imported HR emails**. The manual address field accepts commas, semicolons, spaces or newlines and can be combined with either selection. Duplicate addresses are merged before preview and sending. Manual-only addresses use a generic recruiter greeting and organisation name; they are not added to the HR database. Changing the recipient set requires a new preview.

Sending is a PostgreSQL-backed queue processed while the backend is running. Default limits are `OUTREACH_DAILY_LIMIT=100` attempts per rolling 24 hours and `OUTREACH_INTERVAL_SECONDS=10` between messages. A large list continues over multiple days. Messages are sent individually, repeated copies of the same message/resume are skipped, and recipients plus attachment contents are frozen when queued. Sent/failed/queued counts and cancellation are available in the dialog. Interrupted deliveries are marked for verification rather than resent automatically. Provider rejections and quota pauses appear in history. This feature does not automatically send mail on import or resume extraction. Apply migrations before starting the backend; `OUTREACH_ENABLED=false` stops the sender worker.

A full-stack AI job discovery and resume-matching platform with resume extraction, source collection, and recruiter contacts.

## Resume-driven collection

- Select **Use as primary** in Resume Profile. The first uploaded resume is primary automatically; migration selects a suitable existing resume for legacy accounts.
- Extracting a profile queues collection against the user's **primary parsed resume** after extraction succeeds. **Collect matching jobs** also starts a run manually.
- Collectors score candidates before storing jobs. Only scores **strictly greater than 80** are saved, with job details, application URLs, and user/resume-specific match results. Matching uses the existing local weighted rules engine; Gemini extracts the resume profile.
- Collection respects the user's persisted `preferred_job_country`. For India, explicit India locations and recognised Indian cities qualify. With `include_international_remote` enabled, overseas fully remote jobs also qualify when the posting explicitly accepts applicants in India or worldwide. Structured applicant-location requirements are retained with the job; country-restricted and unspecified remote eligibility are excluded. The same policy applies to employer feeds, career pages, Telegram, imported postings, and resume reanalysis.
- Collection runs daily at **08:00 Asia/Kolkata**, using active configured sources for each active user's primary profile. Startup after 08:00 catches up that day's run. The backend must remain running for scheduled execution; PostgreSQL records the queue and prevents duplicate daily runs across API workers.
- Duplicate jobs are identified by normalized title, company and location. A database unique index and transaction locks prevent repeated or concurrent collection from adding another job or match record. Existing duplicate jobs are consolidated by migration while preserving HR contacts and the latest result per user/resume.
- Telegram uses the same **score > 80** filter before saving jobs. It reads all messages in the daily window instead of only the newest 100, and extends the window back to the previous successful fetch after downtime. `TELEGRAM_LOOKBACK_HOURS=24` sets the minimum re-scan window. Reposts are deduplicated; failed ingestion leaves the fetch checkpoint unchanged so the next run can retry.
- The worker checks the queue every 30 seconds. Interrupted runs retry after restart, and source failures do not stop other sources. Latest status and per-source results appear under Resume Profile and at `GET /api/v1/collections`.
- Jobs and match records expire **30 days after creation/first extraction**, even if a later collection sees the same job again. Cleanup runs with the worker. Resumes, profiles, accounts, job sources, and HR contacts remain. Contacts retain a snapshot of the job and application link when the job is deleted.

Apply the new database migration before restarting the backend:

```powershell
cd backend
.\venv\Scripts\python.exe -m alembic upgrade head
```

Configuration: `COLLECTION_ENABLED=true`, `COLLECTION_TIMEZONE=Asia/Kolkata`, `JOB_RETENTION_DAYS=30`. Set `COLLECTION_ENABLED=false` to disable the background worker, including cleanup. Windows installations need the `tzdata` dependency for the IANA timezone database.

### Career pages and job boards

Greenhouse, Lever, RSS, and Telegram collectors remain available. Configure employer career pages as `career_page` sources using the existing `/api/v1/job-sources` API. Public career pages are parsed for Schema.org `JobPosting` JSON-LD, following up to 12 same-site job links. `{query}` in a source URL is replaced with the primary resume's professional title.

The worker registers public search-page attempts for Naukri, LinkedIn, Indeed, Hirist Tech, Foundit, and Instahyre. This is **best-effort public-page support**, not a guaranteed integration with those platforms. Login, JavaScript-only rendering, robots restrictions, HTTP blocks, and missing structured postings are reported as source failures. There is no CAPTCHA/login bypass. Authorized feeds or accessible employer career sources are needed where public collection is unavailable. Disable any unwanted source through the existing job-sources API.

`python -m scripts.collect_india_jobs --user-id UUID` registers and collects the verified employer feeds used for India discovery. `--import-file PATH --skip-employers` imports full Indeed records retrieved through Firecrawl, with the same scoring, country filtering, and deduplication. Firecrawl's Codex connection is available to the chat; connecting it does not supply API credentials to the backend. Imported Indeed records are snapshots; unattended daily Indeed refresh is not configured. Public discovery files are stored locally under `backend/private_storage/discovery/` and excluded from Git.

Collection verification (the PostgreSQL tests create and remove isolated test schemas):

```powershell
cd backend
$env:TEST_POSTGRES='1'
.\venv\Scripts\python.exe -m pytest tests/test_collection_flow.py -q
```

## Stack
- Frontend: React, TypeScript, Vite, Material UI, Axios, React Router
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, PyJWT, Argon2
- Infrastructure: PostgreSQL, Redis, Docker Compose

## Prerequisites
- Docker Desktop (recommended for PostgreSQL and Redis)
- Python 3.12+
- Node.js 20+

## Start infrastructure and backend
1. Copy `.env.example` to `.env`.
2. Change `SECRET_KEY` to a long random value.
3. Start services: `docker compose up --build -d`.
4. Apply database migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```
5. API docs: http://localhost:8000/docs
6. Health check: http://localhost:8000/health

## Start frontend
```bash
cd frontend
npm install
# Create frontend/.env.local if needed:
# VITE_API_URL=http://localhost:8000/api/v1
npm run dev
```
Open http://localhost:5173.

## Authentication endpoints
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh` (rotates the refresh cookie and issues a new access token)\n- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

Login returns a short-lived access token and sets a refresh-token cookie. Access tokens are kept in frontend memory, not localStorage. Refresh cookies are HttpOnly and rotated on refresh. For production, add server-side refresh-token persistence/revocation (for example, hashed token records with token-family reuse detection), CSRF protection appropriate to the deployment, and rate limiting.

## Phase 1 notes
- User records use UUID primary keys and unique indexed email addresses.
- Passwords are hashed with Argon2.
- API routes, service logic, repositories, schemas, models and configuration are separated.
- Dashboard metrics are intentionally empty until real data connectors are implemented.
- Redis is provisioned for later Celery work; job collection and AI agents are not part of Phase 1.

## Development checks
Backend:
```bash
cd backend
python -m venv .venv
# activate the environment, then:
pip install -r requirements.txt
pytest
```
Frontend:
```bash
cd frontend
npm install
npm run build
```

## Security before production
Use HTTPS, set `COOKIE_SECURE=true`, rotate secrets, configure a restrictive CORS allowlist, add refresh-token rotation/revocation, rate limiting, audit logging, backups and observability. Do not expose PostgreSQL or Redis publicly.
