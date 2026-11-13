
import uuid
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobListResponse,
)
from app.services.job_service import JobService


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobService(db).create_job(payload)



@router.get(
    "",
    response_model=JobListResponse,
)
def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),

    search: str | None = Query(default=None),
    location: str | None = Query(default=None),

    employment_type: str | None = Query(default=None),
    work_mode: str | None = Query(default=None),

    experience_min: int | None = Query(default=None, ge=0),
    experience_max: int | None = Query(default=None, ge=0),

    skill: str | None = Query(default=None),

    source_type: Literal[
        "telegram",
        "whatsapp",
        "career_page",
        "greenhouse",
        "lever",
        "rss",
        "api",
        "manual",
    ] | None = Query(default=None),

    is_active: bool = Query(default=True),

    sort_by: Literal[
        "posted_at",
        "created_at",
        "title",
        "company_name",
        "location",
    ] = "posted_at",

    sort_order: Literal["asc", "desc"] = "desc",

    db: Session = Depends(get_db),
):
    return JobService(db).list_jobs(
        page=page,
        page_size=page_size,
        search=search,
        location=location,
        employment_type=employment_type,
        work_mode=work_mode,
        experience_min=experience_min,
        experience_max=experience_max,
        skill=skill,
        source_type=source_type,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
    )



@router.get(
    "/{job_id}",
    response_model=JobResponse,
)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return JobService(db).get_job(job_id)


@router.put(
    "/{job_id}",
    response_model=JobResponse,
)
def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobService(db).update_job(
        job_id=job_id,
        payload=payload,
    )


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
)
def delete_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobService(db).delete_job(job_id)
