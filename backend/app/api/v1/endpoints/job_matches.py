
# app/api/v1/endpoints/job_matches.py

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.job_match import JobMatchResponse
from app.services.job_match_service import JobMatchService


router = APIRouter(
    prefix="/job-matches",
    tags=["Job Matches"],
)


@router.post(
    "/analyze/{job_id}",
    response_model=JobMatchResponse,
    status_code=status.HTTP_200_OK,
)
def analyze_job_match(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobMatchService(db).analyze_job(
        job_id=job_id,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[JobMatchResponse],
)
def list_job_matches(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    matched_only: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobMatchService(db).list_user_matches(
        current_user=current_user,
        page=page,
        page_size=page_size,
        matched_only=matched_only,
    )


@router.get(
    "/{match_id}",
    response_model=JobMatchResponse,
)
def get_job_match(
    match_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobMatchService(db).get_user_match(
        match_id=match_id,
        current_user=current_user,
    )

@router.post(
    "/analyze-all",
    status_code=status.HTTP_200_OK,
)
def analyze_all_jobs(
    batch_size: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobMatchService(db).analyze_all_jobs(
        current_user=current_user,
        batch_size=batch_size,
    )