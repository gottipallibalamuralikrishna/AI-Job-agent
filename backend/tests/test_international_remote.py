from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.collectors.career_page import normalize_posting
from app.collectors.greenhouse import GreenhouseCollector
from app.collectors.lever import LeverCollector
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_source import JobSource
from app.services.job_ingestion_service import JobIngestionService
from app.services.job_location import matches_job_location
from app.services.job_match_service import JobMatchService
from app.services.job_matching_service import JobMatchingService
from tests.test_collection_flow import db, seed_profile


@pytest.mark.parametrize("changes,allowed", [
    ({"location": "Remote - Worldwide"}, True),
    ({"location": "Home based - Worldwide", "work_mode": None}, True),
    ({"location": "Berlin, Germany", "description": "This fully remote role is open to candidates worldwide."}, True),
    ({"description": "This role is open to applicants from India."}, True),
    ({"remote_eligible_locations": ["India", "Germany"]}, True),
    ({"remote_eligible_locations": ["IN"]}, True),
    ({"remote_eligible_locations": ["Bengaluru"]}, True),
    ({"remote_eligible_locations": ["Worldwide"]}, True),
    ({"description": "Our company has a global remote team."}, False),
    ({"location": "Remote - United States", "description": "Work from anywhere."}, False),
    ({"location": "Remote - Brazil", "description": "Work from anywhere."}, False),
    ({"location": "Home based - EMEA", "work_mode": None, "description": "We hire candidates worldwide."}, False),
    ({"location": "Remote", "description": "Work from anywhere. You must be based in Peru."}, False),
    ({"location": "Remote - Worldwide", "description": "Applicants from Canada only."}, False),
    ({"location": "Remote - Worldwide", "description": "Candidates must reside in the U.S."}, False),
    ({"location": "Remote - Worldwide", "description": "Worldwide applicants except India."}, False),
    ({"location": "Remote - Worldwide", "description": "We cannot hire in India."}, False),
    ({"location": "Remote - Worldwide", "description": "This role is only available in Spain."}, False),
    ({"location": "Remote - Worldwide", "remote_eligible_locations": ["United States"]}, False),
    ({"location": "Bengaluru, India", "remote_eligible_locations": ["United States"]}, False),
    ({"work_mode": "hybrid", "description": "Work from anywhere in the world."}, False),
    ({"work_mode": "onsite", "description": "Work from anywhere in the world."}, False),
    ({"location": "Remote - Worldwide", "description": "This is not a remote role."}, False),
    ({}, False),
])
def test_only_explicitly_eligible_international_remote_jobs(changes, allowed):
    job = {"location": "Remote", "work_mode": "remote", "description": "Frontend developer using React"}
    job.update(changes)
    assert matches_job_location(job, "India", True) is allowed


def test_overseas_remote_is_opt_in_and_domestic_jobs_remain_eligible():
    assert not matches_job_location({"location": "Remote - Worldwide", "work_mode": "remote"}, "India", False)
    assert matches_job_location({"location": "Bengaluru", "work_mode": "remote"}, "India", False)
    assert matches_job_location({"location": "Hyderabad", "work_mode": "hybrid"}, "India", False)


def test_jsonld_retains_applicant_countries():
    job = normalize_posting({"title": "Frontend Developer", "jobLocationType": "TELECOMMUTE",
        "jobLocation": {"address": {"addressCountry": "Germany"}},
        "applicantLocationRequirements": [{"@type": "Country", "name": "India"},
                                           {"@type": "Country", "name": "Germany"}]},
        "https://example.com/jobs/1", "Example")
    assert job["remote_eligible_locations"] == ["India", "Germany"]
    assert matches_job_location(job, "India", True)


def test_employer_feeds_retain_explicit_remote_eligibility(monkeypatch):
    greenhouse = GreenhouseCollector()
    lever = LeverCollector()
    try:
        monkeypatch.setattr(greenhouse, "get_json", lambda url: {"jobs": [{
            "id": 1, "title": "Frontend Developer", "location": {"name": "Remote"},
            "content": "React", "metadata": [{"name": "Applicant locations", "value": ["India"]}]}]})
        monkeypatch.setattr(lever, "get_json", lambda url: [{"id": "one", "text": "Frontend Developer",
            "workplaceType": "remote", "allLocations": ["Remote", "India", "United States"],
            "categories": {"location": "Remote"}}])
        source = SimpleNamespace(name="Example", external_source_id="example")
        assert greenhouse.fetch_jobs(source)[0]["remote_eligible_locations"] == ["India"]
        assert lever.fetch_jobs(source)[0]["remote_eligible_locations"] == ["India", "United States"]
    finally:
        greenhouse.close()
        lever.close()


def remote_job(external_id, **changes):
    return {"external_id": external_id, "title": f"Frontend Developer {external_id}", "company_name": "Example",
        "location": "Remote", "work_mode": "remote", "remote_eligible_locations": ["India", "Germany"],
        "description": "Build frontend web applications with React and TypeScript",
        "required_skills": ["React", "TypeScript"], "application_url": "https://example.com/jobs/1", **changes}


def test_ingestion_applies_eligibility_threshold_and_user_preferences(db, monkeypatch):
    user, _, profile = seed_profile(db)
    domestic_user, _, domestic_profile = seed_profile(db)
    user.preferred_job_country = domestic_user.preferred_job_country = "India"
    user.include_international_remote = True
    source = JobSource(name="Remote feed", source_type="api")
    db.add(source)
    db.commit()
    original = JobMatchingService.analyze
    def score(profile, job):
        result = original(profile, job)
        result["match_score"] = 80 if job.external_id == "cutoff" else 90
        return result
    monkeypatch.setattr(JobMatchingService, "analyze", score)
    jobs = [remote_job("open"), remote_job("cutoff"),
        remote_job("restricted", remote_eligible_locations=["United States"]),
        remote_job("unknown", remote_eligible_locations=[])]
    service = JobIngestionService(db)
    for _ in range(2):
        result = service.collect_from_source(source.id, [profile, domestic_profile], deepcopy(jobs))
        assert result["failed"] == 0
    assert db.query(Job).count() == db.query(JobMatch).count() == 1
    assert db.query(JobMatch).one().user_id == user.id
    assert db.query(JobMatch).one().match_score == 90
    assert db.query(Job).one().remote_eligible_locations == ["India", "Germany"]
    # A source changing its country requirements must remove the old match.
    service.collect_from_source(source.id, [profile], [remote_job("open", remote_eligible_locations=["United States"])])
    assert db.query(JobMatch).count() == 0


def test_bulk_and_single_analysis_obey_remote_eligibility(db):
    user, _, _ = seed_profile(db)
    user.preferred_job_country, user.include_international_remote = "India", True
    allowed = Job(**remote_job("open"))
    restricted = Job(**remote_job("restricted", remote_eligible_locations=["United States"]))
    db.add_all([allowed, restricted])
    db.commit()
    service = JobMatchService(db)
    service.analyze_all_jobs(user)
    assert db.query(JobMatch).one().job_id == allowed.id
    assert service.analyze_job(allowed.id, user).match_score > 80
    with pytest.raises(HTTPException) as exc:
        service.analyze_job(restricted.id, user)
    assert exc.value.status_code == 422
    user.include_international_remote = False
    service.analyze_all_jobs(user)
    assert db.query(JobMatch).count() == 0
