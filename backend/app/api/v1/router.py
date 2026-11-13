
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    resumes,
    jobs,
    job_sources,
    job_matches,
    recruiter_contacts
)

api_router = APIRouter()
api_router.include_router(recruiter_contacts.router)
api_router.include_router(auth.router)
api_router.include_router(resumes.router)
api_router.include_router(jobs.router)
api_router.include_router(job_sources.router)
api_router.include_router(job_matches.router)
