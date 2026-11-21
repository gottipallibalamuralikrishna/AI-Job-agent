
from contextlib import asynccontextmanager
from threading import Event, Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app):
    stop = Event()
    worker = None
    mail_worker = None
    if settings.outreach_enabled:
        from app.services.outreach_service import worker_loop as mail_loop
        mail_worker = Thread(target=mail_loop, args=(stop,), daemon=True, name='recruiter-email')
        mail_worker.start()
    if settings.collection_enabled:
        from app.services.collection_service import worker_loop
        worker = Thread(target=worker_loop, args=(stop,), daemon=True, name="job-collection")
        worker.start()
    yield
    stop.set()
    if mail_worker:
        mail_worker.join(timeout=1)
    if worker:
        # Network calls have bounded timeouts; do not block API shutdown.
        worker.join(timeout=1)


# --------------------------------------------------
# FastAPI Application
# --------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description="AI-powered Job Hunting and Resume Management API",
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# CORS Configuration
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# API Router Registration
# --------------------------------------------------

app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)


# --------------------------------------------------
# Root Endpoint
# --------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {
        "success": True,
        "message": "JobPilot AI API is running",
    }


# --------------------------------------------------
# Health Check Endpoint
# --------------------------------------------------

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "success": True,
        "status": "healthy",
        "application": settings.app_name,
        "environment": settings.environment,
    }
