
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.resume import ResumeResponse
from app.services.resume_service import ResumeService
from uuid import UUID

from app.schemas.resume import ResumeParseResponse
from app.services.resume_processing_service import ResumeProcessingService

from app.schemas.profile import ResumeProfileResponse
from app.services.profile_extraction_service import (
    ProfileExtractionService,
)
from fastapi import HTTPException,status
from app.models.resume_profile import ResumeProfile
from app.schemas.resume import ResumeResponse
from app.schemas.profile import (
    CandidateProfile,
    ResumeProfileResponse,
)
from app.models.resume import Resume
from app.schemas.resume import ResumeResponse
from app.models.user import User


router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ResumeService(db).upload_resume(
        file=file,
        current_user=current_user,
    )

@router.post(
    "/{resume_id}/parse",
    response_model=ResumeParseResponse,
)
def parse_resume(
    resume_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = ResumeProcessingService(db).parse_resume(
        resume_id=resume_id,
        current_user=current_user,
    )

    return {
        "id": resume.id,
        "original_filename": resume.original_filename,
        "parsing_status": resume.parsing_status,
        "extracted_character_count": len(
            resume.extracted_text or ""
        ),
    }

@router.post(
    "/{resume_id}/extract-profile",
    response_model=ResumeProfileResponse,
)
def extract_resume_profile(
    resume_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = ProfileExtractionService(db).extract_and_save(
        resume_id=resume_id,
        current_user=current_user,
    )

    return profile



@router.get("", response_model=list[ResumeResponse])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )

    return resumes


@router.get(
    "/{resume_id}/profile",
    response_model=ResumeProfileResponse,
)
def get_resume_profile(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify that the resume belongs to the logged-in user
    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    # Fetch the extracted profile
    profile = (
        db.query(ResumeProfile)
        .filter(
            ResumeProfile.resume_id == resume_id,
            ResumeProfile.user_id == current_user.id,
        )
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile has not been extracted yet.",
        )

    return profile


@router.put(
    "/{resume_id}/profile",
    response_model=ResumeProfileResponse,
)
def update_resume_profile(
    resume_id: UUID,
    payload: CandidateProfile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = (
        db.query(ResumeProfile)
        .filter(
            ResumeProfile.resume_id == resume_id,
            ResumeProfile.user_id == current_user.id,
        )
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Resume profile not found",
        )

    profile.profile_data = payload.model_dump(mode="json")

    db.commit()
    db.refresh(profile)

    return profile
