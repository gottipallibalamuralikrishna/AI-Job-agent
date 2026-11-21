import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.collectors.career_page import PostingPage, normalize_posting, postings
from app.core.config import settings
from app.models.job import Job
from app.models.job_contact import JobContact
from app.models.job_match import JobMatch
from app.models.job_source import JobSource
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.models.user import User
from app.schemas.job_contact import RecruiterContactResponse
from app.services.collection_service import cleanup_expired, daily_due, enqueue_primary
from app.services.gemini_resume_service import GeminiResumeService
from app.services.job_ingestion_service import JobIngestionService
from app.services.job_matching_service import JobMatchingService
from app.services.recruiter_contact_service import RecruiterContactService
from app.services import collection_service
from app.services.job_match_service import JobMatchService
from app.services.job_location import matches_country


def test_daily_boundary_is_india_time():
    assert daily_due(datetime(2026, 11, 15, 2, 29, tzinfo=timezone.utc))[0] is False
    assert daily_due(datetime(2026, 11, 15, 2, 30, tzinfo=timezone.utc)) == (True, "2026-11-15")


def test_jsonld_graph_preserves_application_details():
    page = PostingPage()
    page.feed('''<script type="application/ld+json">{"@graph":[{"@type":"JobPosting",
      "title":"Frontend Developer", "hiringOrganization":{"name":"Example"},
      "url":"/jobs/123", "description":"React and TypeScript",
      "jobLocation":{"address":{"addressLocality":"Chennai"}}}]}</script>''')
    items = list(postings(page.scripts))
    assert len(items) == 1
    job = normalize_posting(items[0], "https://example.com/careers", "Fallback")
    assert job["application_url"] == "https://example.com/jobs/123"
    assert job["company_name"] == "Example"
    assert job["location"] == "Chennai"


def test_gemini_methods_belong_to_service():
    assert callable(GeminiResumeService.extract_profile)
    assert callable(GeminiResumeService._generate_content)


@pytest.mark.parametrize("description,expected", [
    ("6–15 years’ experience in web development", 6),
    ("Experience: 5 Years+", 5),
    ("Experience: 3-4 years", 3),
    ("At least 3 years of experience", 3),
    ("5-8yrs", 5),
])
def test_experience_requirements_are_not_treated_as_unknown(description, expected):
    assert JobMatchingService._extract_required_experience(description) == expected


def test_country_filter_does_not_assume_remote_eligibility():
    assert matches_country("Bengaluru", "India")
    assert matches_country("Remote, India", "India")
    assert not matches_country("United Kingdom", "India")
    assert not matches_country("Remote", "India")
    assert not matches_country(None, "India")


def test_plural_rest_apis_are_recognized():
    assert "rest api" in JobMatchingService._extract_candidate_skills({"technical_skills": ["REST APIs"]})


@pytest.fixture
def db():
    if os.getenv("TEST_POSTGRES") != "1":
        pytest.skip("Set TEST_POSTGRES=1 to test in an isolated PostgreSQL schema")
    base = create_engine(settings.database_url)
    schema = "collection_test_" + uuid.uuid4().hex
    with base.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    isolated = create_engine(settings.database_url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with isolated.begin() as connection:
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        with Session(isolated, expire_on_commit=False) as session:
            yield session
    finally:
        isolated.dispose()
        with base.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        base.dispose()


def seed_profile(db):
    user = User(email=f"{uuid.uuid4()}@example.com", full_name="Test User", hashed_password="unused")
    db.add(user)
    db.flush()
    resume = Resume(user_id=user.id, original_filename="test.pdf", stored_filename=str(uuid.uuid4()),
                    storage_path="unused", content_type="application/pdf", file_size_bytes=10,
                    parsing_status="parsed", is_primary=True)
    db.add(resume)
    db.flush()
    profile = ResumeProfile(user_id=user.id, resume_id=resume.id, profile_data={
        "professional_title": "Frontend Developer", "technical_skills": ["React", "TypeScript"],
        "total_experience_years": 3,
        "work_experience": [{"responsibilities": ["frontend web application development"]}]})
    db.add(profile)
    db.commit()
    return user, resume, profile


def test_primary_queue_uses_primary_and_daily_is_idempotent(db):
    user, resume, _ = seed_profile(db)
    other = Resume(user_id=user.id, original_filename="other.pdf", stored_filename=str(uuid.uuid4()),
                   storage_path="unused", content_type="application/pdf", file_size_bytes=10,
                   parsing_status="parsed", is_primary=False)
    db.add(other)
    db.commit()
    run = enqueue_primary(db, user.id, "daily:test")
    assert run.resume_id == resume.id
    assert enqueue_primary(db, user.id, "daily:test").id == run.id


def test_strict_score_filter_and_rejected_job_contacts(db, monkeypatch):
    _, _, profile = seed_profile(db)
    source = JobSource(name="Fixture", source_type="career_page", source_url="https://example.com")
    db.add(source)
    db.commit()

    class Collector:
        def fetch_jobs(self, source):
            return [{"external_id": str(score), "title": f"Frontend Developer {score}", "company_name": "Example",
                     "description": "React TypeScript frontend web application", "required_skills": ["React", "TypeScript"],
                     "application_url": f"https://example.com/jobs/{score}",
                     "contacts": [{"contact_type": "email", "contact_value": f"hr{score}@example.com"}]}
                    for score in (79, 80, 81)]

        def close(self):
            pass

    original = JobMatchingService.analyze
    def score(profile, job):
        result = original(profile, job)
        result["match_score"] = float(job.external_id)
        return result
    monkeypatch.setitem(JobIngestionService.COLLECTORS, "career_page", Collector)
    monkeypatch.setattr(JobMatchingService, "analyze", score)
    service = JobIngestionService(db)
    result = service.collect_from_source(source.id, [profile])
    assert result["created"] == 1
    assert [j.external_id for j in db.query(Job).all()] == ["81"]
    assert db.query(JobMatch).one().match_score == 81
    assert db.query(JobContact).count() == 3
    assert db.query(JobContact).filter(JobContact.job_id.is_(None)).count() == 2
    service.collect_from_source(source.id, [profile])
    assert db.query(JobContact).count() == 3


def test_retention_preserves_contacts_and_profile_and_visibility(db):
    user, resume, _ = seed_profile(db)
    source = JobSource(name="Fixture", source_type="telegram")
    db.add(source)
    db.flush()
    now = datetime.now(timezone.utc)
    old = Job(source_id=source.id, title="Old role", company_name="Example", created_at=now - timedelta(days=30))
    fresh = Job(source_id=source.id, title="Fresh role", company_name="Example", created_at=now - timedelta(days=29))
    db.add_all([old, fresh])
    db.flush()
    JobIngestionService(db)._save_contacts(old, [{"contact_type": "email", "contact_value": "hr@example.com"}], source)
    db.add(JobMatch(user_id=user.id, resume_id=resume.id, job_id=old.id, match_score=90, decision="matched"))
    db.commit()
    assert cleanup_expired(db, now) == {"jobs_deleted": 1, "matches_deleted": 1}
    db.expire_all()
    contact = db.query(JobContact).one()
    assert contact.job_id is None
    assert RecruiterContactResponse.model_validate(contact).job.title == "Old role"
    assert RecruiterContactService.list_contacts(db, search="Old role", source_type="telegram")["total"] == 1
    assert RecruiterContactService.get_contact_stats(db)["jobs_with_contacts"] == 1
    assert db.query(Job).one().title == "Fresh role"
    assert db.query(Resume).count() == db.query(ResumeProfile).count() == db.query(User).count() == 1


def test_worker_continues_after_source_failure_and_records_results(db, monkeypatch):
    user, _, _ = seed_profile(db)
    first = JobSource(name="Failure", source_type="rss")
    second = JobSource(name="Success", source_type="greenhouse")
    disabled = JobSource(
        name="Himalayas", source_type="api",
        external_source_id=collection_service.HIMALAYAS_SOURCE_ID, is_active=False,
    )
    db.add_all([first, second, disabled])
    run = enqueue_primary(db, user.id)
    db.commit()
    run_id = run.id
    monkeypatch.setattr(collection_service, "BOARD_SOURCES", {})
    monkeypatch.setattr(collection_service, "daily_due", lambda now: (False, "unused"))
    monkeypatch.setattr(collection_service, "engine", db.get_bind())
    monkeypatch.setattr(collection_service, "SessionLocal", lambda: Session(db.get_bind()))
    def collect(self, source_id, profiles):
        if source_id == first.id:
            raise RuntimeError("Source blocked")
        return dict.fromkeys(("total_fetched", "created", "updated", "skipped", "failed", "contacts_saved"), 0)
    monkeypatch.setattr(JobIngestionService, "collect_from_source", collect)
    collection_service.tick()
    db.expire_all()
    from app.models.collection_run import CollectionRun
    result = db.get(CollectionRun, run_id)
    assert result.status == "partial"
    assert {r["source"]: r["status"] for r in result.results} == {"Failure": "failed", "Success": "completed"}


def test_bulk_analysis_saves_only_primary_resume_scores_above_80(db, monkeypatch):
    user, resume, _ = seed_profile(db)
    db.add_all([Job(title=f"Frontend Developer {score}", company_name="Example", external_id=str(score),
                    description="React TypeScript frontend web application", required_skills=["React", "TypeScript"])
                for score in (80, 81)])
    db.commit()
    original = JobMatchingService.analyze
    def score(profile, job):
        result = original(profile, job)
        result["match_score"] = float(job.external_id)
        return result
    monkeypatch.setattr(JobMatchingService, "analyze", score)
    result = JobMatchService(db).analyze_all_jobs(user)
    assert result["processed"] == 2
    assert result["not_matched"] == 1
    record = db.query(JobMatch).one()
    assert record.match_score == 81 and record.resume_id == resume.id


def test_primary_selection_rejects_another_users_resume(db):
    from fastapi import HTTPException
    from app.api.v1.endpoints.resumes import select_primary_resume
    first, _, _ = seed_profile(db)
    _, other_resume, _ = seed_profile(db)
    with pytest.raises(HTTPException) as exc:
        select_primary_resume(other_resume.id, db, first)
    assert exc.value.status_code == 404


def test_imported_jobs_respect_india_preference_and_use_no_collector(db):
    user, _, profile = seed_profile(db)
    user.preferred_job_country = "India"
    source = JobSource(name="Imported jobs", source_type="api")
    db.add(source)
    db.commit()
    jobs = [{"external_id": location, "title": "Frontend Developer", "company_name": "Example",
             "location": location, "required_skills": ["React", "TypeScript"],
             "description": "Build frontend web applications", "application_url": "https://example.com/apply"}
            for location in ("Bengaluru, India", "London, United Kingdom")]
    result = JobIngestionService(db).collect_from_source(source.id, [profile], jobs)
    assert result["created"] == 1
    assert db.query(Job).one().location == "Bengaluru, India"
    assert db.query(JobMatch).one().match_score > 80
