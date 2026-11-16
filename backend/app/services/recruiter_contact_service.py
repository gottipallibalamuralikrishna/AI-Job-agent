from math import ceil
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.job import Job
from app.models.job_contact import JobContact
from app.models.job_source import JobSource


class RecruiterContactService:

    @staticmethod
    def list_contacts(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        contact_type: str | None = None,
        source_type: str | None = None,
        job_id: UUID | None = None,
    ):
        query = (
            select(JobContact)
            .outerjoin(Job, JobContact.job_id == Job.id)
            .outerjoin(JobSource, Job.source_id == JobSource.id)
            .options(joinedload(JobContact.job))
        )

        count_query = (
            select(func.count(JobContact.id))
            .outerjoin(Job, JobContact.job_id == Job.id)
            .outerjoin(JobSource, Job.source_id == JobSource.id)
        )

        if search:
            term = f"%{search.strip()}%"
            condition = or_(
                JobContact.contact_value.ilike(term),
                JobContact.contact_name.ilike(term),
                Job.title.ilike(term),
                Job.company_name.ilike(term),
                JobContact.job_snapshot["title"].astext.ilike(term),
                JobContact.job_snapshot["company_name"].astext.ilike(term),
            )
            query = query.where(condition)
            count_query = count_query.where(condition)

        if contact_type:
            query = query.where(JobContact.contact_type == contact_type)
            count_query = count_query.where(
                JobContact.contact_type == contact_type
            )

        if source_type:
            query = query.where(func.coalesce(JobContact.source_type, JobSource.source_type) == source_type)
            count_query = count_query.where(
                func.coalesce(JobContact.source_type, JobSource.source_type) == source_type
            )

        if job_id:
            query = query.where(JobContact.job_id == job_id)
            count_query = count_query.where(
                JobContact.job_id == job_id
            )

        total = db.scalar(count_query) or 0

        query = (
            query
            .order_by(JobContact.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        contacts = db.scalars(query).unique().all()

        return {
            "items": contacts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": ceil(total / page_size) if total else 0,
        }

    @staticmethod
    def get_contact(
        db: Session,
        contact_id: UUID,
    ):
        query = (
            select(JobContact)
            .options(joinedload(JobContact.job))
            .where(JobContact.id == contact_id)
        )

        return db.scalars(query).unique().first()

    @staticmethod
    def get_contact_stats(db: Session):
        counts = {
            "email": 0,
            "phone": 0,
            "linkedin": 0,
            "telegram": 0,
            "website": 0,
            "application_url": 0,
        }

        rows = db.execute(
            select(
                JobContact.contact_type,
                func.count(JobContact.id),
            ).group_by(JobContact.contact_type)
        ).all()

        for contact_type, count in rows:
            if contact_type in counts:
                counts[contact_type] = count

        jobs_with_contacts = db.scalar(
            select(func.count(func.distinct(func.coalesce(
                cast(JobContact.job_id, String), JobContact.job_snapshot["id"].astext))))
        ) or 0

        return {
            "total_contacts": sum(counts.values()),
            "total_emails": counts["email"],
            "total_phones": counts["phone"],
            "total_linkedin": counts["linkedin"],
            "total_telegram": counts["telegram"],
            "total_websites": counts["website"],
            "total_application_urls": counts["application_url"],
            "jobs_with_contacts": jobs_with_contacts,
        }
