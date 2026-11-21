import asyncio
import importlib.util
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from types import SimpleNamespace

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.collectors import telegram
from app.collectors.telegram import TelegramCollector, build_job_data
from app.models.collection_run import CollectionRun
from app.models.job import Job
from app.models.job_contact import JobContact
from app.models.job_match import JobMatch
from app.models.job_source import JobSource
from app.models.resume_profile import ResumeProfile
from app.services.collection_service import next_worker_delay, queue_daily_runs
from app.services.job_ingestion_service import JobIngestionService
from app.services.job_matching_service import JobMatchingService
from app.services.job_service import JobService
from tests.test_collection_flow import db, seed_profile


def test_worker_wakes_at_eight_india_time():
    assert next_worker_delay(datetime(2026, 11, 15, 2, 29, 50, tzinfo=timezone.utc)) == 10
    assert next_worker_delay(datetime(2026, 11, 15, 2, 28, tzinfo=timezone.utc)) == 30


def test_daily_queue_runs_once_each_day_at_eight(db):
    user, _, _ = seed_profile(db)
    queue_daily_runs(db, datetime(2026, 11, 15, 2, 29, tzinfo=timezone.utc))
    assert db.query(CollectionRun).count() == 0
    for _ in range(2):
        queue_daily_runs(db, datetime(2026, 11, 15, 2, 30, tzinfo=timezone.utc))
    assert db.query(CollectionRun).count() == 1
    queue_daily_runs(db, datetime(2026, 11, 16, 2, 29, tzinfo=timezone.utc))
    assert db.query(CollectionRun).count() == 1
    queue_daily_runs(db, datetime(2026, 11, 16, 2, 30, tzinfo=timezone.utc))
    assert db.query(CollectionRun).count() == 2
    assert {r.run_key for r in db.query(CollectionRun)} == {
        f"daily:2026-11-15:{user.id}", f"daily:2026-11-16:{user.id}"}


def collector_without_credentials():
    collector = TelegramCollector.__new__(TelegramCollector)
    collector.api_id, collector.api_hash, collector.session_path = 1, "unused", "unused"
    collector.lookback_hours = 24
    return collector


def test_compact_channel_post_preserves_location_and_application_url():
    body = ("Senior Frontend Engineer - Fleet Management\nVerkada, San Mateo, CA\n"
            "https://www.linkedin.com/jobs/view/senior-frontend-engineer-at-verkada-4489192084")
    job = build_job_data(SimpleNamespace(id=114299, date=datetime.now(timezone.utc), message=body),
                         "findfrontendjobs")
    assert job['title'] == 'Senior Frontend Engineer - Fleet Management'
    assert job['company_name'] == 'Verkada'
    assert job['location'] == 'San Mateo, CA'
    assert job['application_url'] == body.splitlines()[2]
    assert job['source_message_url'] == 'https://t.me/findfrontendjobs/114299'
    assert job['required_skills'] == []
    from app.services.job_location import matches_job_location
    assert not matches_job_location(job, 'India', True)


@pytest.mark.parametrize('url', [
    'https://www.linkedin.com/posts/frontend-news',
    'https://linkedin.com.evil.example/jobs/view/123',
    'https://example.com/jobs/view/123',
])
def test_compact_parser_requires_an_actual_job_link(url):
    assert not telegram.is_job_post(f'Frontend Engineer\nExample, India\n{url}')


def test_telegram_catches_up_after_server_downtime():
    collector = collector_without_credentials()
    now = datetime(2026, 11, 15, 2, 30, tzinfo=timezone.utc)
    recent = SimpleNamespace(last_fetched_at=now - timedelta(hours=1))
    old = SimpleNamespace(last_fetched_at=now - timedelta(days=3))
    assert collector.collection_cutoff(recent, now) == now - timedelta(days=1)
    assert collector.collection_cutoff(old, now) == old.last_fetched_at - timedelta(minutes=5)


def test_telegram_reads_more_than_100_recent_messages(monkeypatch):
    now = datetime.now(timezone.utc)
    seen = []
    class Client:
        def __init__(self, *args):
            pass
        async def connect(self):
            pass
        async def disconnect(self):
            pass
        async def is_user_authorized(self):
            return True
        async def get_entity(self, name):
            return name
        async def iter_messages(self, entity, limit):
            assert limit is None
            for i in range(150):
                seen.append(i)
                yield SimpleNamespace(id=i, date=now, message="We are hiring a frontend developer")
            yield SimpleNamespace(id=999, date=now - timedelta(days=2), message="Old hiring post")
    monkeypatch.setattr(telegram, "TelegramClient", Client)
    jobs = asyncio.run(collector_without_credentials()._fetch_messages(
        SimpleNamespace(source_url="https://t.me/testjobs", last_fetched_at=None)))
    assert len(jobs) == len(seen) == 150


def test_telegram_saves_strictly_above_80_and_reposts_only_once(db, monkeypatch):
    _, _, profile = seed_profile(db)
    source = JobSource(name="Telegram test", source_type="telegram", source_url="https://t.me/testjobs")
    db.add(source)
    db.commit()
    def message(number):
        text = ("We are hiring!\nRole: Frontend Developer\nCompany: Example\nLocation: Bengaluru\n"
                "Skills: React, TypeScript\nExperience: 3 years\nBuild frontend web applications\n"
                "Apply: https://example.com/jobs/frontend")
        return build_job_data(SimpleNamespace(id=number, date=datetime.now(timezone.utc), message=text), "testjobs")
    class Collector:
        def fetch_jobs(self, source):
            return [message(1), message(2), message(3)]
        def close(self):
            pass
    original = JobMatchingService.analyze
    def analyze(profile, job):
        result = original(profile, job)
        result["match_score"] = 80 if job.external_id.endswith(":1") else 80.01
        return result
    monkeypatch.setitem(JobIngestionService.COLLECTORS, "telegram", Collector)
    monkeypatch.setattr(JobMatchingService, "analyze", analyze)
    service = JobIngestionService(db)
    for _ in range(2):
        assert service.collect_from_source(source.id, [profile])["failed"] == 0
    assert db.query(Job).count() == db.query(JobMatch).count() == 1
    assert db.query(JobMatch).one().match_score == 80.01


def test_concurrent_sources_reuse_one_job_and_match(db):
    _, _, profile = seed_profile(db)
    sources = [JobSource(name=name, source_type=kind) for name, kind in (("Channel", "telegram"), ("Career", "greenhouse"))]
    db.add_all(sources)
    db.commit()
    source_ids, profile_id = [s.id for s in sources], profile.id
    barrier = Barrier(2)
    def collect(source_id):
        with Session(db.get_bind()) as session:
            candidate = session.get(ResumeProfile, profile_id)
            barrier.wait(timeout=10)
            return JobIngestionService(session).collect_from_source(source_id, [candidate], [{
                "external_id": "frontend-1", "title": "Frontend Developer", "company_name": "Example",
                "location": "Bengaluru", "description": "Build frontend web applications with React and TypeScript",
                "required_skills": ["React", "TypeScript"], "application_url": "https://example.com/jobs/frontend"}])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(collect, source_ids))
    assert sum(result["created"] for result in results) == 1
    assert sum(result["failed"] for result in results) == 0
    db.expire_all()
    assert db.query(Job).count() == db.query(JobMatch).count() == 1


def test_database_rejects_duplicate_hashes(db):
    fingerprint = JobService.generate_job_hash("Frontend Developer", "Example", "Bengaluru")
    assert fingerprint == JobService.generate_job_hash(" frontend   DEVELOPER ", "EXAMPLE", "bengaluru")
    db.add(Job(title="Frontend Developer", company_name="Example", job_hash=fingerprint))
    db.commit()
    db.add(Job(title="frontend developer", company_name="Example", job_hash=fingerprint))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert db.query(Job).count() == 1


def test_unique_hash_migration_merges_existing_jobs_without_losing_contacts(db):
    spec = importlib.util.spec_from_file_location("unique_hash_migration",
        Path(__file__).parents[1] / "alembic/versions/c71e_unique_job_hash.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with db.get_bind().begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
    user, resume, _ = seed_profile(db)
    now = datetime.now(timezone.utc)
    fingerprint = JobService.generate_job_hash("Frontend Developer", "Example", "Bengaluru")
    original = Job(title="Frontend Developer", company_name="Example", job_hash=fingerprint,
                   created_at=now - timedelta(days=10))
    duplicate = Job(title="Frontend Developer", company_name="Example", job_hash=fingerprint,
                    created_at=now)
    db.add_all([original, duplicate])
    db.flush()
    old_id, duplicate_id = original.id, duplicate.id
    for index, job in enumerate((original, duplicate)):
        db.add(JobContact(job_id=job.id, contact_type="email", contact_value="hr@example.com",
            job_snapshot={"id": str(job.id), "title": job.title, "company_name": job.company_name}))
        db.add(JobMatch(user_id=user.id, resume_id=resume.id, job_id=job.id, decision="matched",
            match_score=90 + index, updated_at=now + timedelta(seconds=index)))
    db.commit()
    with db.get_bind().begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
    db.expire_all()
    assert db.query(Job).one().id == old_id
    assert db.get(Job, duplicate_id) is None
    assert db.query(JobMatch).one().match_score == 91
    assert db.query(JobMatch).one().job_id == old_id
    assert db.query(JobContact).count() == 2
    assert db.query(JobContact).filter(JobContact.job_id.is_(None)).count() == 1
