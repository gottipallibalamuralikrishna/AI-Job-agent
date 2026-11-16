"""Database-backed collection queue and daily retention maintenance."""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, text

from app.core.config import settings
from app.collectors.himalayas import SEARCH_URL, SOURCE_ID as HIMALAYAS_SOURCE_ID
from app.db.session import SessionLocal, engine
from app.models.collection_run import CollectionRun
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_source import JobSource
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.models.user import User
from app.services.job_ingestion_service import JobIngestionService

logger = logging.getLogger(__name__)
LOCK_ID = 82614081
BOARD_SOURCES = {
    "Naukri": "https://www.naukri.com/{query}-jobs",
    "LinkedIn": "https://www.linkedin.com/jobs/search/?keywords={query}",
    "Indeed": "https://in.indeed.com/jobs?q={query}",
    "Hirist Tech": "https://www.hirist.tech/search?q={query}",
    "Foundit": "https://www.foundit.in/srp/results?query={query}",
    "Instahyre": "https://www.instahyre.com/search-jobs/?search={query}",
}


def primary_profiles(db):
    return (db.query(ResumeProfile).join(Resume, Resume.id == ResumeProfile.resume_id)
            .join(User, User.id == Resume.user_id)
            .filter(Resume.is_primary.is_(True), Resume.parsing_status == "parsed", User.is_active.is_(True)).all())


def enqueue_primary(db, user_id, run_key=None):
    profile = next((p for p in primary_profiles(db) if p.user_id == user_id), None)
    if profile is None:
        return None
    key = run_key or f"manual:{uuid.uuid4()}"
    existing = db.query(CollectionRun).filter_by(run_key=key).first()
    if existing:
        return existing
    run = CollectionRun(user_id=user_id, resume_id=profile.resume_id,
                        run_key=key, status="queued", results=[])
    db.add(run)
    db.flush()
    return run


def cleanup_expired(db, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=settings.job_retention_days)
    # FK SET NULL preserves HR contacts and their immutable job snapshots.
    himalayas_sources = select(JobSource.id).where(JobSource.external_source_id == HIMALAYAS_SOURCE_ID)
    expired = (Job.created_at <= cutoff) | (
        Job.source_id.in_(himalayas_sources) & (Job.expires_at <= now)
    )
    old_ids = select(Job.id).where(expired)
    matches = db.execute(delete(JobMatch).where(
        (JobMatch.job_id.in_(old_ids)) | (JobMatch.created_at <= cutoff))).rowcount
    jobs = db.execute(delete(Job).where(expired)).rowcount
    db.execute(delete(CollectionRun).where(CollectionRun.finished_at <= cutoff))
    db.commit()
    return {"jobs_deleted": jobs, "matches_deleted": matches}


def daily_due(now):
    local = now.astimezone(ZoneInfo(settings.collection_timezone))
    return local.hour >= 8, local.date().isoformat()


def queue_daily_runs(db, now):
    due, day = daily_due(now)
    if due:
        for profile in primary_profiles(db):
            enqueue_primary(db, profile.user_id, f"daily:{day}:{profile.user_id}")
    db.commit()


def next_worker_delay(now):
    local = now.astimezone(ZoneInfo(settings.collection_timezone))
    scheduled = local.replace(hour=8, minute=0, second=0, microsecond=0)
    if local < scheduled:
        return min(30.0, (scheduled - local).total_seconds())
    return 30.0


def tick():
    # A dedicated session advisory lock serializes all workers and is released
    # by PostgreSQL if a process dies. Queued/running runs survive restarts.
    with engine.connect() as lock_connection:
        if not lock_connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_ID}):
            return
        try:
            with SessionLocal() as db:
                now = datetime.now(timezone.utc)
                cleanup_expired(db, now)
                if not db.query(JobSource).filter_by(external_source_id=HIMALAYAS_SOURCE_ID).first():
                    db.add(JobSource(name="Himalayas", source_type="api", source_url=SEARCH_URL,
                                     external_source_id=HIMALAYAS_SOURCE_ID))
                for name, url in BOARD_SOURCES.items():
                    if not db.query(JobSource).filter_by(external_source_id=f"builtin:{name}").first():
                        db.add(JobSource(name=name, source_type="career_page", source_url=url,
                                         external_source_id=f"builtin:{name}"))
                queue_daily_runs(db, now)
                # A running record means a previous process died after claiming
                # it; the advisory lock guarantees that it is safe to retry.
                run = (db.query(CollectionRun).filter(CollectionRun.status.in_(["queued", "running"]))
                       .order_by(CollectionRun.created_at).first())
                if run is None:
                    return
                run.status = "running"
                run.results = []
                db.commit()
                try:
                    profile = next((p for p in primary_profiles(db)
                                    if p.user_id == run.user_id and p.resume_id == run.resume_id), None)
                    if profile is None:
                        raise ValueError("The queued resume is no longer the primary parsed resume")
                    sources = db.query(JobSource).filter(JobSource.is_active.is_(True)).all()
                    results = []
                    for source in sources:
                        if JobIngestionService.collector_for(source) is None:
                            continue
                        source_id, name = source.id, source.name
                        try:
                            result = JobIngestionService(db).collect_from_source(source_id, [profile])
                            # Store only JSON-native counters and status information.
                            results.append({"source": name, "status": "partial" if result["failed"] else "completed",
                                            **{k: result[k] for k in ("total_fetched", "created", "updated", "skipped", "failed", "contacts_saved")}})
                        except Exception as exc:
                            db.rollback()
                            logger.exception("Collection failed for %s", name)
                            results.append({"source": name, "status": "failed",
                                            "error": str(getattr(exc, "detail", str(exc)))})
                        run.results = list(results)
                        db.commit()
                    succeeded = sum(r["status"] == "completed" for r in results)
                    run.status = "completed" if results and succeeded == len(results) else "partial" if succeeded else "failed"
                except Exception as exc:
                    db.rollback()
                    run.status, run.error = "failed", str(exc)
                    logger.exception("Collection run failed")
                run.finished_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            lock_connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_ID})
            lock_connection.commit()


def worker_loop(stop):
    while not stop.is_set():
        try:
            tick()
        except Exception:
            logger.exception("Collection worker tick failed; check migrations and database connectivity")
        stop.wait(next_worker_delay(datetime.now(timezone.utc)))
