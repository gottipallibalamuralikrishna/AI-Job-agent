
import logging
import os

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.collectors.greenhouse import GreenhouseCollector
from app.collectors.lever import LeverCollector
from app.collectors.rss import RSSCollector
from app.collectors.telegram import TelegramCollector

from app.models.job import Job
from app.models.job_contact import JobContact
from app.models.job_source import JobSource
from app.models.user import User

from app.services.job_service import JobService
from app.services.job_match_service import JobMatchService


logger = logging.getLogger(__name__)


class JobIngestionService:

    COLLECTORS = {
        "greenhouse": GreenhouseCollector,
        "lever": LeverCollector,
        "rss": RSSCollector,
        "telegram": TelegramCollector,
    }

    def __init__(self, db: Session):
        self.db = db

    def _save_contacts(
        self,
        job: Job,
        contacts: list[dict],
    ) -> int:
        """
        Save all extracted contacts without creating duplicates.
        """

        saved = 0

        for contact in contacts:

            contact_type = contact.get("contact_type")
            contact_value = contact.get("contact_value")

            if not contact_type or not contact_value:
                continue

            existing = (
                self.db.query(JobContact)
                .filter(
                    JobContact.job_id == job.id,
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
                    contact_type=contact_type,
                    contact_value=contact_value,
                    contact_name=contact.get("contact_name"),
                    is_primary=bool(contact.get("is_primary", False)),
                    is_verified=False,
                )
            )

            saved += 1

        return saved

    def collect_from_source(
        self,
        source_id: UUID,
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

        if collector_class is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Collector is not implemented for "
                    f"source type: {source.source_type}"
                ),
            )

        collector = collector_class()

        created = 0
        updated = 0
        skipped = 0
        failed = 0
        contacts_saved = 0

        raw_jobs = []
        newly_created_job_ids = []

        try:

            raw_jobs = collector.fetch_jobs(source)

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

                    job_hash = JobService.generate_job_hash(
                        title=title,
                        company_name=company_name,
                        location=data.get("location"),
                    )

                    result = None
                    target_job = None

                    with self.db.begin_nested():

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
                            )

                    if result == "created":
                        created += 1
                        newly_created_job_ids.append(
                            target_job.id
                        )

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

            source.last_fetched_at = datetime.now(timezone.utc)

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
                "processed": 0,
                "matched": 0,
                "failed": 0,
            }

            auto_match_enabled = (
                os.getenv(
                    "AUTO_MATCH_NEW_JOBS",
                    "true",
                ).lower()
                in ("true", "1", "yes")
            )

            if auto_match_enabled and newly_created_job_ids:
                matching_summary = self._match_new_jobs(
                    newly_created_job_ids
                )

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
                    "Unable to collect jobs from the selected source."
                ),
            ) from exc

        finally:
            try:
                collector.close()
            except Exception:
                logger.exception(
                    "Failed to close collector for source=%s",
                    source.name,
                )

    def _match_new_jobs(
        self,
        job_ids: list[UUID],
    ) -> dict[str, int]:

        processed = 0
        matched = 0
        failed = 0

        try:
            users = self.db.query(User).all()
            matcher = JobMatchService(self.db)

            for job_id in job_ids:
                for user in users:

                    try:
                        result = matcher.analyze_job(
                            job_id=job_id,
                            current_user=user,
                        )

                        processed += 1

                        if getattr(result, "decision", None) == "matched":
                            matched += 1

                    except Exception:
                        failed += 1

                        logger.exception(
                            "AI matching failed for "
                            "job_id=%s user_id=%s",
                            job_id,
                            user.id,
                        )

        except Exception:
            logger.exception(
                "Unable to initialize automatic job matching."
            )
            failed += len(job_ids)

        return {
            "processed": processed,
            "matched": matched,
            "failed": failed,
        }
