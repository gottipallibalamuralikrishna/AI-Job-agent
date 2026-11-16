"""Bridge Gmail/Firecrawl discovery into local scoring and persistence.

The automation passes job postings, not mailbox contents or credentials.
"""
import argparse
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionLocal, engine
from app.models.collection_run import CollectionRun
from app.models.user import User
from app.services.collection_service import LOCK_ID, primary_profiles
from app.services.discovered_job_service import DiscoveredBatch, import_batch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=uuid.UUID)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--context", action="store_true")
    parser.add_argument("--schema", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.schema:
        print(json.dumps(DiscoveredBatch.model_json_schema()))
        return
    batch = DiscoveredBatch.model_validate_json(args.input.read_text(encoding="utf-8")) if args.input else None
    if args.validate:
        if batch is None:
            parser.error("--input is required for validation")
        print(json.dumps({"valid": True, "jobs": len(batch.jobs), "sources": len(batch.source_results)}))
        return
    if args.user_id is None:
        parser.error("--user-id is required")
    if args.context:
        with SessionLocal() as db:
            user = db.get(User, args.user_id)
            profile = next((p for p in primary_profiles(db) if p.user_id == args.user_id), None)
            if user is None or profile is None:
                raise ValueError("Primary parsed resume profile not found")
            latest = (db.query(CollectionRun).filter(CollectionRun.user_id == args.user_id,
                CollectionRun.run_key.like("external:%"), CollectionRun.status == "completed")
                .order_by(CollectionRun.finished_at.desc()).first())
            since = (latest.finished_at - timedelta(days=1)) if latest else datetime.now(timezone.utc) - timedelta(days=7)
            print(json.dumps({"resume_id": str(profile.resume_id), "country": user.preferred_job_country,
                "include_international_remote": user.include_international_remote,
                "professional_title": profile.profile_data.get("professional_title"),
                "experience_years": profile.profile_data.get("total_experience_years"),
                "skills": profile.profile_data.get("technical_skills", []), "search_since": since.isoformat()}))
        return
    if batch is None:
        parser.error("--input is required for import")
    with engine.connect() as lock:
        lock.execute(text("SELECT pg_advisory_lock(:key)"), {"key": LOCK_ID})
        try:
            with SessionLocal() as db:
                print(json.dumps(import_batch(db, args.user_id, batch)))
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_ID})
            lock.commit()


if __name__ == "__main__":
    main()
