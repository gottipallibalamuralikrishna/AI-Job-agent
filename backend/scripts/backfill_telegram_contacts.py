import argparse
import logging
import re
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models.job import Job
from app.models.job_contact import JobContact
from app.models.job_source import JobSource


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)

PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"
)

URL_PATTERN = re.compile(
    r"https?://[^\s<>\]\[)\"']+",
    re.IGNORECASE,
)

TELEGRAM_USERNAME_PATTERN = re.compile(
    r"(?<![\w/])@([A-Za-z0-9_]{5,32})"
)

HR_NAME_PATTERN = re.compile(
    r"(?:HR|Recruiter|Talent Acquisition|Hiring Manager)"
    r"\s*(?:Name)?\s*[:\-]\s*([A-Za-z][A-Za-z .'-]{1,60})",
    re.IGNORECASE,
)


def clean_value(value: str) -> str:
    return value.strip().strip(".,;:!?)]}\"'<>").strip()


def extract_contact_name(text: str) -> str | None:
    match = HR_NAME_PATTERN.search(text)

    if not match:
        return None

    name = clean_value(match.group(1))

    if len(name) < 2:
        return None

    return name


def normalize_phone(value: str) -> str | None:
    value = clean_value(value)

    digits = re.sub(r"\D", "", value)

    # Avoid treating job IDs, years, or short numeric values as phone numbers.
    if len(digits) < 10 or len(digits) > 15:
        return None

    return value


def classify_url(url: str) -> tuple[str, str] | None:
    url = clean_value(url)

    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return None

    if not host:
        return None

    if "linkedin.com" in host:
        return "linkedin", url

    if "t.me" in host or "telegram.me" in host:
        return "telegram", url

    # URLs pointing to a job application form are classified separately.
    application_terms = (
        "apply",
        "application",
        "jobs",
        "careers",
        "greenhouse",
        "lever",
        "workday",
        "recruit",
    )

    if any(term in url.lower() for term in application_terms):
        return "application_url", url

    return "website", url


def extract_contacts(
    text: str,
    fallback_application_url: str | None = None,
) -> list[dict]:
    contacts = []
    seen = set()

    def add_contact(
        contact_type: str,
        contact_value: str,
        contact_name: str | None = None,
    ):
        value = clean_value(contact_value)

        if not value:
            return

        key = (contact_type, value.lower())

        if key in seen:
            return

        seen.add(key)

        contacts.append(
            {
                "contact_type": contact_type,
                "contact_value": value,
                "contact_name": contact_name,
                "is_primary": False,
                "is_verified": False,
            }
        )

    contact_name = extract_contact_name(text)

    # Email addresses
    for email in EMAIL_PATTERN.findall(text):
        add_contact(
            "email",
            email,
            contact_name,
        )

    # Phone numbers
    for phone in PHONE_PATTERN.findall(text):
        normalized = normalize_phone(phone)

        if normalized:
            add_contact(
                "phone",
                normalized,
                contact_name,
            )

    # URLs
    for url in URL_PATTERN.findall(text):
        classified = classify_url(url)

        if classified:
            contact_type, contact_value = classified

            add_contact(
                contact_type,
                contact_value,
                contact_name,
            )

    # Telegram usernames
    for username in TELEGRAM_USERNAME_PATTERN.findall(text):
        add_contact(
            "telegram",
            f"https://t.me/{username}",
            contact_name,
        )

    # Include the application's URL stored on the job.
    if fallback_application_url:
        classified = classify_url(fallback_application_url)

        if classified:
            contact_type, contact_value = classified

            add_contact(
                contact_type,
                contact_value,
                contact_name,
            )

    return contacts


def backfill_contacts(
    db,
    dry_run: bool = False,
    limit: int | None = None,
    batch_size: int = 100,
):
    query = (
        select(Job)
        .join(JobSource, Job.source_id == JobSource.id)
        .where(
            JobSource.source_type == "telegram",
            Job.raw_source_text.is_not(None),
            Job.raw_source_text != "",
        )
        .order_by(Job.created_at.asc())
    )

    if limit:
        query = query.limit(limit)

    jobs = db.scalars(query).all()

    logger.info("Telegram jobs found: %s", len(jobs))

    stats = {
        "jobs_scanned": 0,
        "jobs_with_contacts": 0,
        "contacts_found": 0,
        "contacts_created": 0,
        "contacts_skipped": 0,
        "jobs_without_contacts": 0,
        "errors": 0,
    }

    for start in range(0, len(jobs), batch_size):
        batch = jobs[start:start + batch_size]

        for job in batch:
            stats["jobs_scanned"] += 1

            try:
                extracted = extract_contacts(
                    text=job.raw_source_text or "",
                    fallback_application_url=job.application_url,
                )

                if not extracted:
                    stats["jobs_without_contacts"] += 1
                    continue

                stats["jobs_with_contacts"] += 1
                stats["contacts_found"] += len(extracted)

                existing_rows = db.scalars(
                    select(JobContact).where(
                        JobContact.job_id == job.id
                    )
                ).all()

                existing_keys = {
                    (
                        contact.contact_type,
                        contact.contact_value.strip().lower(),
                    )
                    for contact in existing_rows
                }

                for contact_data in extracted:
                    key = (
                        contact_data["contact_type"],
                        contact_data["contact_value"].strip().lower(),
                    )

                    if key in existing_keys:
                        stats["contacts_skipped"] += 1
                        continue

                    if dry_run:
                        stats["contacts_created"] += 1
                        existing_keys.add(key)
                        continue

                    db.add(
                        JobContact(
                            job_id=job.id,
                            **contact_data,
                        )
                    )

                    existing_keys.add(key)
                    stats["contacts_created"] += 1

            except Exception:
                stats["errors"] += 1
                logger.exception(
                    "Failed to backfill contacts for job %s",
                    job.id,
                )

        if not dry_run:
            try:
                db.commit()
                logger.info(
                    "Processed batch ending at job %s",
                    start + len(batch),
                )
            except SQLAlchemyError:
                db.rollback()
                logger.exception("Database commit failed for batch")
                stats["errors"] += len(batch)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Backfill recruiter contacts from existing Telegram jobs."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and count contacts without inserting records.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of Telegram jobs to process.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of jobs to process before committing.",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero")

    if args.batch_size < 1:
        parser.error("--batch-size must be greater than zero")

    db = SessionLocal()

    try:
        stats = backfill_contacts(
            db=db,
            dry_run=args.dry_run,
            limit=args.limit,
            batch_size=args.batch_size,
        )

        logger.info("Backfill summary:")
        for key, value in stats.items():
            logger.info("%s: %s", key, value)

        if args.dry_run:
            logger.info("Dry run completed. No database records were inserted.")
        else:
            logger.info("Backfill completed.")

    finally:
        db.close()


if __name__ == "__main__":
    main()