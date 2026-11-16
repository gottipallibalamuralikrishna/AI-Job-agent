
import logging
from types import SimpleNamespace
import uuid

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.collectors.greenhouse import GreenhouseCollector
from app.collectors.lever import LeverCollector
from app.collectors.rss import RSSCollector
from app.collectors.telegram import TelegramCollector

from app.models.job import Job
from app.models.job_contact import JobContact
from app.models.job_source import JobSource
from app.models.user import User
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.models.job_match import JobMatch
from app.services.job_matching_service import JobMatchingService
from app.collectors.career_page import CareerPageCollector

from app.services.job_service import JobService
from app.services.job_match_service import JobMatchService
from app.services.job_location import infer_work_mode, matches_job_location


logger = logging.getLogger(__name__)


class JobIngestionService:

    COLLECTORS = {
        "greenhouse": GreenhouseCollector,
        "lever": LeverCollector,
        "rss": RSSCollector,
        "telegram": TelegramCollector,
        "career_page": CareerPageCollector,
    }

    def __init__(self, db: Session):
        self.db = db

    def _save_contacts(
        self,
        job: Job,
        contacts: list[dict],
        source: JobSource,
    ) -> int:
        """
        Save all extracted contacts without creating duplicates.
        """

        saved = 0
        snapshot = {"id": str(job.id or uuid.uuid5(uuid.NAMESPACE_URL, str(source.id) + (job.external_id or job.title))),
                    "title": job.title, "company_name": job.company_name,
                    "location": job.location, "application_url": job.application_url,
                    "source_id": str(source.id),
                    "collection_key": f"{source.id}:{job.external_id or job.title}"}

        for contact in contacts:

            contact_type = contact.get("contact_type")
            contact_value = contact.get("contact_value")

            if not contact_type or not contact_value:
                continue

            existing = (
                self.db.query(JobContact)
                .filter(
                    or_(
                        JobContact.job_id == job.id if job.id is not None else False,
                        JobContact.job_snapshot["id"].astext == snapshot["id"],
                        JobContact.job_snapshot["collection_key"].astext == snapshot["collection_key"],
                    ),
                    JobContact.contact_type == contact_type,
                    JobContact.contact_value == contact_value,
                )
                .first()
            )

            if existing:
                # Refresh information without marking it verified.
                if contact.get("contact_name"):
                    existing.contact_name = contact["contact_name"]

                if contact.get("is_primary"):
                    existing.is_primary = True

                continue

            self.db.add(
                JobContact(
                    job_id=job.id,
                    job_snapshot=snapshot,
                    source_type=source.source_type,
                    contact_type=contact_type,
                    contact_value=contact_value,
                    contact_name=contact.get("contact_name"),
                    is_primary=bool(contact.get("is_primary", False)),
                    is_verified=False,
                )
            )

            saved += 1
            self.db.flush()

        return saved

    def collect_from_source(
        self,
        source_id: UUID,
        resume_profiles: list[ResumeProfile] | None = None,
        provided_jobs: list[dict] | None = None,
    ) -> dict[str, Any]:

        source = self.db.get(JobSource, source_id)

        if source is None:
            raise HTTPException(
                status_code=404,
                detail="Job source not found.",
            )

        if not source.is_active:
            raise HTTPException(
                status_code=400,
                detail="Job source is inactive.",
            )

        collector_class = self.COLLECTORS.get(
            source.source_type
        )

        if collector_class is None and provided_jobs is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Collector is not implemented for "
                    f"source type: {source.source_type}"
                ),
            )

        if resume_profiles is None:
            resume_profiles = (self.db.query(ResumeProfile).join(Resume, Resume.id == ResumeProfile.resume_id)
                .join(User, User.id == Resume.user_id)
                .filter(Resume.is_primary.is_(True), Resume.parsing_status == "parsed", User.is_active.is_(True)).all())
        collector = collector_class() if provided_jobs is None else None
        preferences = {user.id: (user.preferred_job_country, user.include_international_remote) for user in self.db.query(User).filter(
            User.id.in_([profile.user_id for profile in resume_profiles])).all()}
        if resume_profiles and collector is not None:
            collector.query = resume_profiles[0].profile_data.get("professional_title") or "software developer"

        created = 0
        updated = 0
        skipped = 0
        failed = 0
        contacts_saved = 0

        raw_jobs = []
        matches_saved = 0

        try:

            fetch_started_at = datetime.now(timezone.utc)
            raw_jobs = provided_jobs if provided_jobs is not None else collector.fetch_jobs(source)

            logger.info(
                "Fetched %s jobs from source %s",
                len(raw_jobs),
                source.name,
            )

            for data in raw_jobs:

                try:
                    # Contacts are stored in their own table.
                    job_contacts = data.pop("contacts", [])

                    external_id = data.get("external_id")

                    if not external_id:
                        skipped += 1
                        continue

                    title = data.get("title")
                    company_name = data.get("company_name")

                    if not title or not company_name:
                        skipped += 1
                        continue

                    data["work_mode"] = infer_work_mode(data)

                    scores = [(profile, JobMatchingService.analyze(profile.profile_data, SimpleNamespace(**data)))
                              for profile in resume_profiles if matches_job_location(data, *preferences.get(profile.user_id, (None, False)))]
                    qualifying = [(profile, score) for profile, score in scores
                                  if score["match_score"] > 80]
                    if not qualifying:
                        # Preserve public HR contacts even when the job does not qualify.
                        transient = Job(**{k: v for k, v in data.items() if hasattr(Job, k)})
                        with self.db.begin_nested():
                            contacts_saved += self._save_contacts(transient, job_contacts, source)
                            existing = self.db.query(Job).filter_by(source_id=source.id, external_id=external_id).first()
                            if existing:
                                for profile in resume_profiles:
                                    self.db.query(JobMatch).filter_by(user_id=profile.user_id,
                                        resume_id=profile.resume_id, job_id=existing.id).delete()
                        skipped += 1
                        continue

                    job_hash = JobService.generate_job_hash(
                        title=title,
                        company_name=company_name,
                        location=data.get("location"),
                    )

                    result = None
                    target_job = None

                    with self.db.begin_nested():

                        JobService(self.db).lock_job_hash(job_hash)

                        existing_job = (
                            self.db.query(Job)
                            .filter(
                                Job.source_id == source.id,
                                Job.external_id == external_id,
                            )
                            .first()
                        )

                        if existing_job:

                            for field, value in data.items():

                                if field in {
                                    "external_id",
                                    "department",
                                }:
                                    continue

                                if hasattr(existing_job, field):
                                    setattr(
                                        existing_job,
                                        field,
                                        value,
                                    )

                            existing_job.job_hash = job_hash

                            target_job = existing_job
                            result = "updated"

                        else:

                            duplicate_job = (
                                self.db.query(Job)
                                .filter(
                                    Job.job_hash == job_hash
                                )
                                .first()
                            )

                            if duplicate_job:

                                # Keep contacts from this source too.
                                target_job = duplicate_job
                                result = "skipped"

                            else:

                                job_data = {
                                    key: value
                                    for key, value in data.items()
                                    if key not in {
                                        "external_id",
                                        "department",
                                    }
                                }

                                new_job = Job(
                                    source_id=source.id,
                                    external_id=external_id,
                                    job_hash=job_hash,
                                    **job_data,
                                )

                                self.db.add(new_job)
                                self.db.flush()

                                target_job = new_job
                                result = "created"

                        # Save contacts for new, updated and duplicate jobs.
                        if target_job and job_contacts:
                            contacts_saved += self._save_contacts(
                                target_job,
                                job_contacts,
                                source,
                            )

                        for profile, score in qualifying:
                            record = self.db.query(JobMatch).filter_by(user_id=profile.user_id,
                                resume_id=profile.resume_id, job_id=target_job.id).first()
                            values = JobMatchService._build_match_values(score)
                            if record:
                                for key, value in values.items():
                                    setattr(record, key, value)
                            else:
                                self.db.add(JobMatch(user_id=profile.user_id, resume_id=profile.resume_id,
                                    job_id=target_job.id, **values))
                        qualified_users = {profile.user_id for profile, _ in qualifying}
                        for profile in resume_profiles:
                            if profile.user_id not in qualified_users:
                                self.db.query(JobMatch).filter_by(user_id=profile.user_id,
                                    resume_id=profile.resume_id, job_id=target_job.id).delete()

                    matches_saved += len(qualifying)
                    if result == "created":
                        created += 1

                    elif result == "updated":
                        updated += 1

                    elif result == "skipped":
                        skipped += 1

                except Exception:

                    failed += 1

                    logger.exception(
                        "Failed to process job external_id=%s "
                        "from source=%s",
                        data.get("external_id"),
                        source.name,
                    )

                    continue

            # Messages arriving during a fetch must remain eligible next time.
            if failed == 0:
                source.last_fetched_at = fetch_started_at

            # Commit jobs and contacts together.
            self.db.commit()

            logger.info(
                "Collection completed for %s. "
                "Created=%s Updated=%s Skipped=%s "
                "Failed=%s Contacts=%s",
                source.name,
                created,
                updated,
                skipped,
                failed,
                contacts_saved,
            )

            matching_summary = {
                "processed": matches_saved,
                "matched": matches_saved,
                "failed": 0,
            }

            return {
                "source_id": str(source.id),
                "source_name": source.name,
                "source_type": source.source_type,
                "total_fetched": len(raw_jobs),
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
                "contacts_saved": contacts_saved,
                "matching": matching_summary,
                "last_fetched_at": source.last_fetched_at,
                "message": "Job collection completed successfully.",
            }

        except HTTPException:
            self.db.rollback()
            raise

        except Exception as exc:

            self.db.rollback()

            logger.exception(
                "Job collection failed for source=%s",
                source.name,
            )

            raise HTTPException(
                status_code=502,
                detail=(
                    f"Unable to collect jobs: {exc}"
                ),
            ) from exc

        finally:
            try:
                if collector is not None:
                    collector.close()
            except Exception:
                logger.exception(
                    "Failed to close collector for source=%s",
                    source.name,
                )
