
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Any
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.models.user import User
from app.services.job_matching_service import JobMatchingService
from app.services.job_location import matches_job_location


class JobMatchService:

    def __init__(self, db: Session):
        self.db = db

    def analyze_job(
        self,
        job_id: uuid.UUID,
        current_user: User,
    ) -> JobMatch:

        # 1. Find the active job
        job = (
            self.db.query(Job)
            .filter(
                Job.id == job_id,
                Job.is_active.is_(True),
            )
            .first()
        )

        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active job not found.",
            )

        # 2. Find the user's latest parsed resume profile.
        # Prefer the primary resume, then the most recently created.
        resume_profile = (
            self.db.query(ResumeProfile)
            .join(
                Resume,
                Resume.id == ResumeProfile.resume_id,
            )
            .filter(
                ResumeProfile.user_id == current_user.id,
                Resume.user_id == current_user.id,
                Resume.parsing_status == "parsed",
                Resume.is_primary.is_(True),
            )
            .order_by(
                Resume.is_primary.desc(),
                Resume.created_at.desc(),
            )
            .first()
        )

        if resume_profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "No parsed resume profile found. "
                    "Upload a resume, parse it, and extract its profile first."
                ),
            )

        profile_data = resume_profile.profile_data or {}

        if not isinstance(profile_data, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid resume profile data.",
            )

        if not profile_data.get("technical_skills"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "No technical skills found in the resume profile. "
                    "Please review and update your extracted profile."
                ),
            )

        # 3. Run the weighted matching engine
        result = JobMatchingService.analyze(
            profile=profile_data,
            job=job,
        )

        # 4. Find an existing result for this user, job and resume.
        # Update the existing record instead of creating duplicates.
        existing_match = (
            self.db.query(JobMatch)
            .filter(
                JobMatch.user_id == current_user.id,
                JobMatch.job_id == job.id,
                JobMatch.resume_id == resume_profile.resume_id,
            )
            .first()
        )

        if result["match_score"] <= 80 or not matches_job_location(job, current_user.preferred_job_country, current_user.include_international_remote):
            if existing_match:
                self.db.delete(existing_match)
                self.db.commit()
            raise HTTPException(status_code=422, detail="Job must score above 80 and satisfy your country preference")

        # 5. Prepare all matching results for database persistence.
        match_values = {
            # Overall matching result
            "match_score": result["match_score"],
            "decision": result["decision"],

            # Technical skill matching
            "matched_skills": result["matched_skills"],
            "missing_skills": result["missing_skills"],
            "candidate_skills": result["candidate_skills"],
            "job_skills": result["job_skills"],
            "matched_skill_count": result["matched_skill_count"],
            "total_job_skills": result["total_job_skills"],

            # Role classification
            "role_family": result["role_family"],
            "candidate_role_family": result["candidate_role_family"],

            # Individual scoring dimensions
            "role_match_score": result["role_match_score"],
            "skill_match_score": result["skill_match_score"],
            "experience_match_score": result["experience_match_score"],
            "responsibility_match_score": (
                result["responsibility_match_score"]
            ),

            # Required and preferred skills
            "required_skills": result["required_skills"],
            "preferred_skills": result["preferred_skills"],
            "missing_preferred_skills": (
                result["missing_preferred_skills"]
            ),

            # Experience comparison
            "required_experience_years": (
                result["required_experience_years"]
            ),
            "candidate_experience_years": (
                result["candidate_experience_years"]
            ),

            # Responsibility comparison
            "matched_responsibility_categories": (
                result["matched_responsibility_categories"]
            ),

            # Explanation and rejection reasons
            "rejection_reasons": result["rejection_reasons"],
            "match_explanation": result["match_explanation"],
        }

        try:
            # 6. Update existing match or create a new one
            if existing_match:

                for field, value in match_values.items():
                    setattr(existing_match, field, value)

                match_record = existing_match

            else:

                match_record = JobMatch(
                    user_id=current_user.id,
                    job_id=job.id,
                    resume_id=resume_profile.resume_id,
                    **match_values,
                )

                self.db.add(match_record)

            # 7. Save changes
            self.db.commit()
            self.db.refresh(match_record)

            return match_record

        except Exception:
            self.db.rollback()
            raise

    def list_user_matches(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        matched_only: bool | None = None,
    ) -> list[JobMatch]:
        from sqlalchemy import column, exists, table

        applications = table("job_applications", column("user_id"), column("job_id"))

        # Only return matches belonging to the authenticated user.
        query = self.db.query(JobMatch).join(Resume, Resume.id == JobMatch.resume_id).filter(
            JobMatch.user_id == current_user.id, Resume.is_primary.is_(True)
        )
        query = query.filter(~exists().where(
            applications.c.user_id == current_user.id,
            applications.c.job_id == JobMatch.job_id,
        ))

        # Filter matched jobs
        if matched_only is True:
            query = query.filter(
                JobMatch.decision == "matched"
            )

        # Filter rejected jobs
        elif matched_only is False:
            query = query.filter(
                JobMatch.decision == "not_matched"
            )

        # Pagination
        offset = (page - 1) * page_size

        return (
            query.order_by(
                JobMatch.match_score.desc(),
                JobMatch.created_at.desc(),
            )
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def get_user_match(
        self,
        match_id: uuid.UUID,
        current_user: User,
    ) -> JobMatch:

        # Retrieve a match only if it belongs to the current user.
        match_record = (
            self.db.query(JobMatch)
            .filter(
                JobMatch.id == match_id,
                JobMatch.user_id == current_user.id,
            )
            .first()
        )

        if match_record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job match not found.",
            )

        return match_record


    def _get_user_resume_profile(
        self,
        current_user: User,
    ) -> ResumeProfile:
        """Get the primary parsed resume profile for the user."""

        resume_profile = (
            self.db.query(ResumeProfile)
            .join(
                Resume,
                Resume.id == ResumeProfile.resume_id,
            )
            .filter(
                ResumeProfile.user_id == current_user.id,
                Resume.user_id == current_user.id,
                Resume.parsing_status == "parsed",
                Resume.is_primary.is_(True),
            )
            .order_by(
                Resume.is_primary.desc(),
                Resume.created_at.desc(),
            )
            .first()
        )

        if resume_profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "No parsed resume profile found. "
                    "Upload a resume, parse it, and extract its profile first."
                ),
            )

        profile_data = resume_profile.profile_data or {}

        if not isinstance(profile_data, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid resume profile data.",
            )

        if not profile_data.get("technical_skills"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No technical skills found in the resume profile.",
            )

        return resume_profile

    @staticmethod
    def _build_match_values(result: dict[str, Any]) -> dict[str, Any]:
        """Convert matching engine output into database fields."""

        return {
            "match_score": result["match_score"],
            "matched_skills": result["matched_skills"],
            "missing_skills": result["missing_skills"],
            "candidate_skills": result["candidate_skills"],
            "job_skills": result["job_skills"],
            "matched_skill_count": result["matched_skill_count"],
            "total_job_skills": result["total_job_skills"],
            "decision": result["decision"],

            "role_family": result["role_family"],
            "candidate_role_family": result["candidate_role_family"],
            "role_match_score": result["role_match_score"],
            "skill_match_score": result["skill_match_score"],
            "experience_match_score": result["experience_match_score"],
            "responsibility_match_score": (
                result["responsibility_match_score"]
            ),

            "required_skills": result["required_skills"],
            "preferred_skills": result["preferred_skills"],
            "missing_preferred_skills": (
                result["missing_preferred_skills"]
            ),

            "required_experience_years": (
                result["required_experience_years"]
            ),
            "candidate_experience_years": (
                result["candidate_experience_years"]
            ),

            "matched_responsibility_categories": (
                result["matched_responsibility_categories"]
            ),
            "rejection_reasons": result["rejection_reasons"],
            "match_explanation": result["match_explanation"],
        }

    def analyze_all_jobs(
        self,
        current_user: User,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """
        Analyze all active jobs against the user's selected resume.

        Jobs are fetched in batches.
        Existing match records are updated.
        New match records are inserted.
        Global Job records are never modified.
        """

        # 1. Validate batch size
        if batch_size < 1 or batch_size > 200:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Batch size must be between 1 and 200.",
            )

        # 2. Get the user's parsed resume
        resume_profile = self._get_user_resume_profile(
            current_user
        )

        profile_data = resume_profile.profile_data or {}

        # 3. Count all active jobs
        total_jobs = (
            self.db.query(Job)
            .filter(Job.is_active.is_(True))
            .count()
        )

        if total_jobs == 0:
            return {
                "resume_id": str(resume_profile.resume_id),
                "total_jobs": 0,
                "processed": 0,
                "matched": 0,
                "not_matched": 0,
                "failed": 0,
                "batch_size": batch_size,
                "message": "No active jobs are available for matching.",
            }

        # 4. Initialize processing counters
        processed = 0
        matched_count = 0
        not_matched_count = 0
        failed_count = 0

        offset = 0

        # 5. Process jobs in batches
        while True:

            jobs = (
                self.db.query(Job)
                .filter(Job.is_active.is_(True))
                .order_by(Job.created_at.asc(), Job.id.asc())
                .offset(offset)
                .limit(batch_size)
                .all()
            )

            if not jobs:
                break

            job_ids = [job.id for job in jobs]

            # Load existing user-specific match records for this batch.
            existing_matches = (
                self.db.query(JobMatch)
                .filter(
                    JobMatch.user_id == current_user.id,
                    JobMatch.resume_id == resume_profile.resume_id,
                    JobMatch.job_id.in_(job_ids),
                )
                .all()
            )

            match_by_job_id = {
                match.job_id: match
                for match in existing_matches
            }

            batch_processed = 0
            batch_matched = 0
            batch_not_matched = 0

            # 6. Analyze each job
            for job in jobs:

                try:
                    result = JobMatchingService.analyze(
                        profile=profile_data,
                        job=job,
                    )

                    match_values = self._build_match_values(result)

                    existing_match = match_by_job_id.get(job.id)

                    if result["match_score"] <= 80 or not matches_job_location(job, current_user.preferred_job_country, current_user.include_international_remote):
                        if existing_match:
                            self.db.delete(existing_match)
                        batch_processed += 1
                        batch_not_matched += 1
                        continue

                    if existing_match:

                        # Update existing result
                        for field, value in match_values.items():
                            setattr(existing_match, field, value)

                    else:

                        # Create new user-specific result
                        match_record = JobMatch(
                            user_id=current_user.id,
                            job_id=job.id,
                            resume_id=resume_profile.resume_id,
                            **match_values,
                        )

                        self.db.add(match_record)

                        # Keep the in-memory map in sync.
                        match_by_job_id[job.id] = match_record

                    batch_processed += 1

                    if result["decision"] == "matched":
                        batch_matched += 1
                    else:
                        batch_not_matched += 1

                except Exception:
                    # Do not stop processing the remaining jobs.
                    failed_count += 1
                    continue

            # 7. Commit each batch.
            if batch_processed > 0:

                try:
                    self.db.commit()

                    processed += batch_processed
                    matched_count += batch_matched
                    not_matched_count += batch_not_matched

                except Exception:
                    self.db.rollback()

                    # The entire batch was rolled back.
                    failed_count += batch_processed

            # Move to the next batch.
            offset += len(jobs)

        # 8. Return processing summary
        return {
            "resume_id": str(resume_profile.resume_id),
            "total_jobs": total_jobs,
            "processed": processed,
            "matched": matched_count,
            "not_matched": not_matched_count,
            "failed": failed_count,
            "batch_size": batch_size,
            "message": (
                "Bulk job matching completed."
                if failed_count == 0
                else "Bulk job matching completed with some failures."
            ),
        }
