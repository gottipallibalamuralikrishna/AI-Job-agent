from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.job_contact import (
    RecruiterContactListResponse,
    RecruiterContactResponse,
    RecruiterContactStatsResponse,
)
from app.services.recruiter_contact_service import RecruiterContactService


router = APIRouter(
    prefix="/recruiter-contacts",
    tags=["Recruiter Contacts"],
)


@router.get(
    "",
    response_model=RecruiterContactListResponse,
)
def list_recruiter_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    contact_type: str | None = Query(
        None,
        pattern="^(email|phone|application_url|linkedin|telegram|website)$",
    ),
    source_type: str | None = Query(
        None,
        pattern="^(telegram|whatsapp|career_page|greenhouse|lever|rss|api|manual)$",
    ),
    job_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RecruiterContactService.list_contacts(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        contact_type=contact_type,
        source_type=source_type,
        job_id=job_id,
    )


@router.get(
    "/stats",
    response_model=RecruiterContactStatsResponse,
)
def recruiter_contact_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RecruiterContactService.get_contact_stats(db)


@router.get(
    "/{contact_id}",
    response_model=RecruiterContactResponse,
)
def get_recruiter_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = RecruiterContactService.get_contact(
        db=db,
        contact_id=contact_id,
    )

    if not contact:
        raise HTTPException(
            status_code=404,
            detail="Recruiter contact not found",
        )

    return contact