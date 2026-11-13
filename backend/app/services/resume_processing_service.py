
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resume import Resume
from app.models.user import User
from app.services.resume_parser import ResumeParser


class ResumeProcessingService:

    def __init__(self, db: Session):
        self.db = db

    def parse_resume(
        self,
        resume_id: UUID,
        current_user: User,
    ) -> Resume:

        resume = (
            self.db.query(Resume)
            .filter(
                Resume.id == resume_id,
                Resume.user_id == current_user.id,
            )
            .first()
        )

        if resume is None:
            raise HTTPException(
                status_code=404,
                detail="Resume not found",
            )

        if resume.parsing_status == "processing":
            raise HTTPException(
                status_code=409,
                detail="Resume is already being processed",
            )

        storage_root = Path(settings.resume_storage_dir)

        if not storage_root.is_absolute():
            storage_root = Path.cwd() / storage_root

        storage_root = storage_root.resolve()
        file_path = Path(resume.storage_path).resolve()

        # Ensure the stored path belongs to our private directory.
        if not file_path.is_relative_to(storage_root):
            raise HTTPException(
                status_code=400,
                detail="Invalid resume storage location",
            )

        if not file_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="Resume file is missing from storage",
            )

        resume.parsing_status = "processing"
        self.db.commit()

        try:
            extracted_text = ResumeParser.extract_text(
                file_path=file_path,
                content_type=resume.content_type,
            )

            resume.extracted_text = extracted_text
            resume.parsing_status = "parsed"

            self.db.commit()
            self.db.refresh(resume)

            return resume

        except Exception:
            self.db.rollback()

            resume = self.db.get(Resume, resume_id)

            if resume is not None:
                resume.parsing_status = "failed"
                self.db.commit()

            raise
