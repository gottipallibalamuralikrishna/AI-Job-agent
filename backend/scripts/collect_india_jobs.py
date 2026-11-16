"""Collect verified employer feeds and optionally import full Firecrawl job records.

Run from backend: python -m scripts.collect_india_jobs --user-id UUID
Only public jobs are fetched; the resume is scored locally.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionLocal, engine
from app.models.job_source import JobSource
from app.models.job_match import JobMatch
from app.models.user import User
from app.services.collection_service import LOCK_ID, primary_profiles
from app.services.job_ingestion_service import JobIngestionService
from app.services.job_match_service import JobMatchService
from app.services.job_location import matches_job_location

SOURCES = [
    ("HighLevel", "lever", "gohighlevel"),
    ("Headout", "greenhouse", "headoutcareers"),
    ("Meltplan", "greenhouse", "meltplan"),
    ("Particle41", "greenhouse", "particle41llc"),
    ("Capco", "greenhouse", "capco"),
    ("Quince", "greenhouse", "quince-careers"),
    ("Eltropy", "greenhouse", "eltropyinc"),
    ("SonicWall", "greenhouse", "sonicwall"),
    ("GHX", "greenhouse", "globalhealthcareexchangeinc"),
    ("Smart Working", "lever", "smart-working-solutions"),
    ("Meesho", "lever", "meesho"),
    ("Neuron7", "lever", "neuron7"),
    ("Coinbase", "greenhouse", "coinbase"),
    ("Canonical", "greenhouse", "canonical"),
    ("Grafana Labs", "greenhouse", "grafanalabs"),
]


def get_source(db, name, kind, token):
    source = db.query(JobSource).filter_by(source_type=kind, external_source_id=token).first()
    if source is None:
        url = f"https://job-boards.greenhouse.io/{token}" if kind == "greenhouse" else f"https://jobs.lever.co/{token}"
        source = JobSource(name=name, source_type=kind, external_source_id=token, source_url=url)
        db.add(source)
        db.commit()
    return source


def normalize_import(records, include_international_remote=False):
    jobs = []
    for item in records:
        if item.get("expired") or not item.get("description_text"):
            continue
        location = item.get("location") or {}
        if location.get("country_code") != "IN" and not include_international_remote:
            continue
        posted = item.get("posted_at")
        jobs.append({
            "external_id": f"indeed:{item['job_key']}",
            "title": item["title"],
            "company_name": (item.get("employer") or {}).get("name") or "Employer not disclosed (Indeed)",
            "location": ", ".join(part for part in (location.get("formatted"),
                "India" if location.get("country_code") == "IN" else location.get("country_code")) if part) or None,
            "work_mode": item.get("work_mode"),
            "remote_eligible_locations": item.get("remote_eligible_locations") or [],
            "description": item["description_text"],
            "application_url": item.get("apply_url") or item["source_url"],
            "source_message_url": item["source_url"],
            "required_skills": [],
            "posted_at": datetime.fromisoformat(posted.replace("Z", "+00:00")) if posted else None,
        })
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--import-file", type=Path)
    parser.add_argument("--skip-employers", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("private_storage/discovery/india_matches.json"))
    args = parser.parse_args()
    import uuid
    user_id = uuid.UUID(args.user_id)
    # Share the worker's lock to avoid overlapping upserts and duplicate matches.
    with engine.connect() as lock:
        lock.execute(text("SELECT pg_advisory_lock(:key)"), {"key": LOCK_ID})
        try:
            with SessionLocal() as db:
                user = db.get(User, user_id)
                if user is None or not user.is_active:
                    raise ValueError("Active user not found")
                profile = next((p for p in primary_profiles(db) if p.user_id == user_id), None)
                if profile is None:
                    raise ValueError("Primary parsed profile not found")
                user.preferred_job_country = "India"
                db.commit()
                service = JobIngestionService(db)
                results = []
                for name, kind, token in ([] if args.skip_employers else SOURCES):
                    source = get_source(db, name, kind, token)
                    try:
                        result = service.collect_from_source(source.id, [profile])
                        summary = {"source": name, **{k: result[k] for k in ("total_fetched", "created", "updated", "skipped", "failed")}}
                    except Exception as exc:
                        db.rollback()
                        summary = {"source": name, "error": str(getattr(exc, "detail", exc))}
                    results.append(summary)
                    print(json.dumps(summary), flush=True)
                if args.import_file:
                    records = json.loads(args.import_file.read_text(encoding="utf-8"))
                    source = get_source(db, "Indeed via Firecrawl", "api", "firecrawl:indeed")
                    result = service.collect_from_source(source.id, [profile], normalize_import(records, user.include_international_remote))
                    summary = {"source": source.name, **{k: result[k] for k in ("total_fetched", "created", "updated", "skipped", "failed")}}
                    results.append(summary)
                    print(json.dumps(summary), flush=True)
                # Apply the current primary resume and domestic/remote policy to
                # existing jobs as well as newly fetched records.
                JobMatchService(db).analyze_all_jobs(user)
                matches = (db.query(JobMatch).filter(JobMatch.resume_id == profile.resume_id,
                    JobMatch.user_id == user_id, JobMatch.match_score > 80)
                    .order_by(JobMatch.match_score.desc()).all())
                shortlist = [{"score": m.match_score, "title": m.job.title, "company": m.job.company_name,
                    "location": m.job.location, "application_url": m.job.application_url,
                    "work_mode": m.job.work_mode, "remote_eligible_locations": m.job.remote_eligible_locations,
                    "required_experience_years": m.required_experience_years,
                    "candidate_experience_years": m.candidate_experience_years,
                    "missing_skills": m.missing_skills} for m in matches
                    if matches_job_location(m.job, user.preferred_job_country, user.include_international_remote)]
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps({"sources": results, "matches": shortlist}, indent=2), encoding="utf-8")
                print(json.dumps({"saved_matches": len(shortlist), "output": str(args.output)}), flush=True)
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_ID})
            lock.commit()


if __name__ == "__main__":
    main()
