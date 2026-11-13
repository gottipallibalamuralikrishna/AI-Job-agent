
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.job_source import (
    JobSourceCreate,
    JobSourceUpdate,
    JobSourceResponse,
    SourceType,
)
from app.services.job_source_service import JobSourceService
from app.services.job_ingestion_service import JobIngestionService


router = APIRouter(
    prefix="/job-sources",
    tags=["Job Sources"],
)


@router.post(
    "",
    response_model=JobSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_source(
    payload: JobSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobSourceService(db).create_source(payload)


@router.get(
    "",
    response_model=list[JobSourceResponse],
)
def list_sources(
    source_type: SourceType | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return JobSourceService(db).list_sources(
        source_type=source_type,
    )


@router.get(
    "/{source_id}",
    response_model=JobSourceResponse,
)
def get_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return JobSourceService(db).get_source(source_id)


@router.put(
    "/{source_id}",
    response_model=JobSourceResponse,
)
def update_source(
    source_id: uuid.UUID,
    payload: JobSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobSourceService(db).update_source(
        source_id=source_id,
        payload=payload,
    )


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_200_OK,
)
def deactivate_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobSourceService(db).deactivate_source(
        source_id=source_id,
    )


@router.post("/{source_id}/collect")
def collect_jobs_from_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return JobIngestionService(db).collect_from_source(
        source_id=source_id,
    )
