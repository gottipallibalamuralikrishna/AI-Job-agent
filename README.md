# JobPilot AI

A full-stack AI job discovery and resume-matching platform. This repository currently implements **Phase 1: foundation and authentication**.

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
