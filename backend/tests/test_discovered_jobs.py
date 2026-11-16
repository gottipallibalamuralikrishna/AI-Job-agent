from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.services.discovered_job_service import DiscoveredBatch, DiscoveredJob, import_batch
from app.models.job import Job
from app.models.job_match import JobMatch
from tests.test_collection_flow import db, seed_profile


def posting(**changes):
    values = dict(source="linkedin", source_url="https://www.linkedin.com/jobs/view/123456/",
        application_url="https://example.com/careers/frontend", title="Frontend Developer",
        company_name="Example", location="Bengaluru, India",
        description="Build frontend web applications with React and TypeScript. "
                    "Own responsive frontend web application development and reusable user interfaces.",
        status="open", checked_at=datetime.now(timezone.utc))
    values.update(changes)
    return DiscoveredJob(**values)


@pytest.mark.parametrize("url", [
    "https://www.linkedin.com/jobs/view/123456/?otpToken=private",
    "https://www.hirist.tech/one-click-apply?jobId=1234",
    "https://example.com/job?jsAuth=private",
    "https://user:password@example.com/job",
])
def test_import_rejects_credentials_and_automatic_action_links(url):
    with pytest.raises(ValidationError):
        posting(application_url=url)


def test_import_normalization_has_stable_identity():
    assert posting().normalized()["external_id"] == posting().normalized()["external_id"]
    with pytest.raises(ValidationError):
        posting(checked_at=datetime(2026, 11, 15))


def test_verified_jobs_import_once_and_unverified_jobs_are_excluded(db):
    user, _, _ = seed_profile(db)
    user.preferred_job_country = "India"
    db.commit()
    batch = DiscoveredBatch(jobs=[posting(), posting(status="unverified", source_url="https://example.com/other")])
    first = import_batch(db, user.id, batch)
    second = import_batch(db, user.id, batch)
    assert first["status"] == second["status"] == "completed"
    assert db.query(Job).count() == db.query(JobMatch).count() == 1
    assert first["results"][0]["created"] == 1
    assert second["results"][0]["created"] == 0
    assert first["results"][0]["unverified"] == 1


def test_empty_import_does_not_claim_success(db):
    user, _, _ = seed_profile(db)
    assert import_batch(db, user.id, DiscoveredBatch())["status"] == "failed"
