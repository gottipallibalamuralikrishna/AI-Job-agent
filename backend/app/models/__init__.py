
# app/models/__init__.py

from app.models.user import User
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.models.job import Job
from app.models.job_source import JobSource
from app.models.job_match import JobMatch
from app.models.job_contact import JobContact
from app.models.collection_run import CollectionRun

__all__ = [
    "User",
    "Resume",
    "ResumeProfile",
    "Job",
    "JobSource",
    "JobMatch",
]
