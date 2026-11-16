
import hashlib
import math
import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.job_source import JobSource
from app.schemas.job import JobCreate, JobUpdate


class JobService:

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def generate_job_hash(
        title: str,
        company_name: str,
        location: str | None,
    ) -> str:
        """
        Generate a normalized hash for duplicate detection.
        """

        def normalize(value: str | None) -> str:
            if not value:
                return ""
            return re.sub(r"\s+", " ", value.strip().lower())

        raw_value = "|".join([
            normalize(title),
            normalize(company_name),
            normalize(location),
        ])

        return hashlib.sha256(
            raw_value.encode("utf-8")
        ).hexdigest()

    def lock_job_hash(self, job_hash: str) -> None:
        # Serialize the same normalized job across API and background ingestion.
        key = int.from_bytes(bytes.fromhex(job_hash)[:8], "big", signed=True)
        self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})

    def create_job(self, payload: JobCreate) -> Job:

        data = payload.model_dump()

        source_id = data.get("source_id")
        external_id = data.get("external_id")

        # Validate source if provided
        if source_id:
            source = self.db.get(JobSource, source_id)

            if source is None:
                raise HTTPException(
                    status_code=404,
                    detail="Job source not found",
                )

        # Check duplicate external ID within the same source
        if source_id and external_id:
            existing_job = (
                self.db.query(Job)
                .filter(
                    Job.source_id == source_id,
                    Job.external_id == external_id,
                )
                .first()
            )

            if existing_job:
                raise HTTPException(
                    status_code=409,
                    detail="Job already exists for this source",
                )

        # Generate duplicate detection hash
        job_hash = self.generate_job_hash(
            title=data["title"],
            company_name=data["company_name"],
            location=data.get("location"),
        )
        self.lock_job_hash(job_hash)

        existing_hash = (
            self.db.query(Job)
            .filter(Job.job_hash == job_hash)
            .first()
        )

        if existing_hash:
            raise HTTPException(
                status_code=409,
                detail="A similar job already exists",
            )

        job = Job(
            **data,
            job_hash=job_hash,
        )

        self.db.add(job)

        try:
            self.db.commit()
            self.db.refresh(job)

        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="This job already exists") from exc
        except Exception:
            self.db.rollback()
            raise

        return job

    def get_job(self, job_id: uuid.UUID) -> Job:

        job = self.db.get(Job, job_id)

        if job is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found",
            )

        return job

    def list_jobs(
    self,
    page: int = 1,
    page_size: int = 10,
    search: str | None = None,
    location: str | None = None,
    employment_type: str | None = None,
    work_mode: str | None = None,
    experience_min: int | None = None,
    experience_max: int | None = None,
    skill: str | None = None,
    source_type: str | None = None,
    is_active: bool = True,
    sort_by: str = "posted_at",
    sort_order: str = "desc",
):

        query = self.db.query(Job).filter(
            Job.is_active == is_active
        )

        # Filter jobs by source type
        if source_type:
            query = (
                query
                .join(JobSource, Job.source_id == JobSource.id)
                .filter(JobSource.source_type == source_type)
        )

        # Search by title or company
        if search:
            search_term = f"%{search.strip()}%"

            query = query.filter(
                or_(
                    Job.title.ilike(search_term),
                    Job.company_name.ilike(search_term),
                )
            )

        # Location filter
        if location:
            query = query.filter(
                Job.location.ilike(f"%{location.strip()}%")
            )

        # Employment type
        if employment_type:
            query = query.filter(
                Job.employment_type == employment_type
            )

        # Work mode
        if work_mode:
            query = query.filter(
                Job.work_mode == work_mode
            )

        # Experience filters
        if experience_min is not None:
            query = query.filter(
                or_(
                    Job.experience_max >= experience_min,
                    Job.experience_max.is_(None),
                )
            )

        if experience_max is not None:
            query = query.filter(
                or_(
                    Job.experience_min <= experience_max,
                    Job.experience_min.is_(None),
                )
            )

        # Required skill filter
        if skill:
            query = query.filter(
                Job.required_skills.contains([skill.strip()])
            )

        # Total matching records
        total = query.count()

        # Allowed sorting columns
        sort_columns = {
            "posted_at": Job.posted_at,
            "created_at": Job.created_at,
            "title": Job.title,
            "company_name": Job.company_name,
            "location": Job.location,
        }

        sort_column = sort_columns.get(sort_by)

        if sort_column is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid sort_by field",
            )

        if sort_order == "asc":
            query = query.order_by(
                sort_column.asc().nullslast()
            )
        elif sort_order == "desc":
            query = query.order_by(
                sort_column.desc().nullslast()
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="sort_order must be asc or desc",
            )

        # Pagination
        offset = (page - 1) * page_size

        jobs = (
            query
            .offset(offset)
            .limit(page_size)
            .all()
        )

        total_pages = math.ceil(total / page_size) if total else 0

        return {
            "items": jobs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def update_job(
        self,
        job_id: uuid.UUID,
        payload: JobUpdate,
    ) -> Job:

        job = self.get_job(job_id)

        update_data = payload.model_dump(
            exclude_unset=True
        )

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update",
            )

        # Required fields cannot be explicitly set to null
        for field in ("title", "company_name"):
            if field in update_data and update_data[field] is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"{field} cannot be null",
                )

        new_title = update_data.get("title", job.title)
        new_company = update_data.get(
            "company_name", job.company_name
        )
        new_location = update_data.get(
            "location", job.location
        )

        experience_min = update_data.get(
            "experience_min", job.experience_min
        )
        experience_max = update_data.get(
            "experience_max", job.experience_max
        )

        salary_min = update_data.get(
            "salary_min", job.salary_min
        )
        salary_max = update_data.get(
            "salary_max", job.salary_max
        )

        if (
            experience_min is not None
            and experience_max is not None
            and experience_min > experience_max
        ):
            raise HTTPException(
                status_code=422,
                detail="Minimum experience cannot exceed maximum experience",
            )

        if (
            salary_min is not None
            and salary_max is not None
            and salary_min > salary_max
        ):
            raise HTTPException(
                status_code=422,
                detail="Minimum salary cannot exceed maximum salary",
            )

        # Check whether the updated job would duplicate another job
        new_hash = self.generate_job_hash(
            new_title,
            new_company,
            new_location,
        )
        self.lock_job_hash(new_hash)

        duplicate = (
            self.db.query(Job)
            .filter(
                Job.job_hash == new_hash,
                Job.id != job.id,
            )
            .first()
        )

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Another similar job already exists",
            )

        for field, value in update_data.items():
            setattr(job, field, value)

        job.job_hash = new_hash

        self.db.commit()
        self.db.refresh(job)

        return job

    def delete_job(self, job_id: uuid.UUID):

        job = self.get_job(job_id)

        self.db.delete(job)
        self.db.commit()

        return {
            "message": "Job deleted successfully"
        }
