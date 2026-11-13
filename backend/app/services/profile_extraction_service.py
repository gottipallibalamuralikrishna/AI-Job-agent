
import logging
import time

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.models.user import User

from app.services.gemini_resume_service import GeminiResumeService


logger = logging.getLogger(__name__)


class ProfileExtractionService:

    def __init__(self, db: Session):
        self.db = db

        # Measure Gemini client initialization
        init_start = time.perf_counter()

        self.gemini_service = GeminiResumeService()

        logger.info(
            "Gemini client initialization took %.3f seconds",
            time.perf_counter() - init_start,
        )

    def extract_and_save(
        self,
        resume_id: UUID,
        current_user: User,
    ) -> ResumeProfile:

        total_start = time.perf_counter()

        try:
            # ----------------------------------------
            # 1. Find resume belonging to this user
            # ----------------------------------------

            db_start = time.perf_counter()

            resume = (
                self.db.query(Resume)
                .filter(
                    Resume.id == resume_id,
                    Resume.user_id == current_user.id,
                )
                .first()
            )

            logger.info(
                "Resume database lookup took %.3f seconds",
                time.perf_counter() - db_start,
            )

            if resume is None:
                raise HTTPException(
                    status_code=404,
                    detail="Resume not found",
                )

            # ----------------------------------------
            # 2. Validate parsed resume
            # ----------------------------------------

            if resume.parsing_status != "parsed":
                raise HTTPException(
                    status_code=409,
                    detail="Resume must be parsed before AI extraction",
                )

            if not resume.extracted_text:
                raise HTTPException(
                    status_code=422,
                    detail="No extracted resume text available",
                )

            # ----------------------------------------
            # 3. Gemini profile extraction
            # ----------------------------------------

            gemini_start = time.perf_counter()

            candidate_profile = (
                self.gemini_service.extract_profile(
                    resume.extracted_text
                )
            )

            gemini_duration = time.perf_counter() - gemini_start

            logger.info(
                "Gemini profile extraction took %.3f seconds",
                gemini_duration,
            )

            # ----------------------------------------
            # 4. Convert Pydantic model to JSON
            # ----------------------------------------

            serialization_start = time.perf_counter()

            profile_data = candidate_profile.model_dump(
                mode="json"
            )

            logger.info(
                "Profile serialization took %.3f seconds",
                time.perf_counter() - serialization_start,
            )

            # ----------------------------------------
            # 5. Find existing profile
            # ----------------------------------------

            db_start = time.perf_counter()

            profile = (
                self.db.query(ResumeProfile)
                .filter(
                    ResumeProfile.resume_id == resume.id,
                    ResumeProfile.user_id == current_user.id,
                )
                .first()
            )

            logger.info(
                "Existing profile lookup took %.3f seconds",
                time.perf_counter() - db_start,
            )

            # ----------------------------------------
            # 6. Create or update profile
            # ----------------------------------------

            if profile:
                profile.profile_data = profile_data

                logger.info(
                    "Updating existing resume profile: %s",
                    resume_id,
                )

            else:
                profile = ResumeProfile(
                    resume_id=resume.id,
                    user_id=current_user.id,
                    profile_data=profile_data,
                )

                self.db.add(profile)

                logger.info(
                    "Creating new resume profile: %s",
                    resume_id,
                )

            # ----------------------------------------
            # 7. Save to PostgreSQL
            # ----------------------------------------

            db_start = time.perf_counter()

            self.db.commit()

            logger.info(
                "Profile database commit took %.3f seconds",
                time.perf_counter() - db_start,
            )

            self.db.refresh(profile)

            # ----------------------------------------
            # 8. Total execution time
            # ----------------------------------------

            total_duration = time.perf_counter() - total_start

            logger.info(
                "Total profile extraction pipeline took %.3f seconds",
                total_duration,
            )

            return profile

        except Exception:
            self.db.rollback()

            logger.exception(
                "Resume profile extraction failed for resume %s",
                resume_id,
            )

            raise
