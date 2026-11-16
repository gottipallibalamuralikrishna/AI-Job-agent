"""Validate externally discovered postings before importing them into the app."""
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import parse_qsl, urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models.collection_run import CollectionRun
from app.models.job_source import JobSource
from app.services.collection_service import primary_profiles
from app.services.job_ingestion_service import JobIngestionService

SourceName = Literal["linkedin", "naukri", "indeed", "hirist", "foundit", "instahyre", "employer"]


class DiscoveredJob(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: SourceName
    source_url: HttpUrl
    application_url: HttpUrl
    title: str = Field(min_length=2, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=100, max_length=200_000)
    status: Literal["open", "opportunities", "unverified", "closed"]
    checked_at: AwareDatetime
    posted_at: datetime | None = None
    work_mode: Literal["remote", "hybrid", "onsite"] | None = None
    remote_eligible_locations: list[str] = Field(default_factory=list)

    @field_validator("source_url", "application_url")
    @classmethod
    def public_links_only(cls, value):
        parsed = urlsplit(str(value))
        if parsed.username or parsed.password:
            raise ValueError("Use a public job URL without credentials")
        if any(term in parsed.path.lower() for term in ("one-click-apply", "unsubscribe", "logout")):
            raise ValueError("Automatic-action links are not public job URLs")
        for key, _ in parse_qsl(parsed.query):
            if any(term in key.lower() for term in ("token", "auth", "signature", "secret", "password")) or key.lower() == "midsig":
                raise ValueError("Remove authentication and session parameters from job URLs")
        return value

    def normalized(self):
        from app.collectors.telegram import extract_contacts
        source_url = str(self.source_url)
        return {
            "external_id": hashlib.sha256(source_url.encode()).hexdigest(),
            "title": self.title,
            "company_name": self.company_name,
            "location": self.location,
            "description": self.description,
            "application_url": str(self.application_url),
            "source_message_url": source_url,
            "posted_at": self.posted_at,
            "work_mode": self.work_mode,
            "remote_eligible_locations": self.remote_eligible_locations,
            "required_skills": [],
            "contacts": extract_contacts(self.description),
        }


class SourceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: SourceName
    status: Literal["completed", "partial", "failed"]
    discovered: int = Field(default=0, ge=0)
    unverified: int = Field(default=0, ge=0)
    error: str | None = None


class DiscoveredBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jobs: list[DiscoveredJob] = Field(default_factory=list, max_length=500)
    source_results: list[SourceResult] = Field(default_factory=list)


def import_batch(db, user_id, batch):
    profile = next((p for p in primary_profiles(db) if p.user_id == user_id), None)
    if profile is None:
        raise ValueError("No active primary parsed resume profile exists")
    run = CollectionRun(user_id=user_id, resume_id=profile.resume_id,
                        run_key=f"external:{uuid.uuid4()}", status="running", results=[])
    db.add(run)
    db.commit()
    results = [r.model_dump(mode="json") for r in batch.source_results]
    try:
        for provider in sorted({job.source for job in batch.jobs}):
            source = db.query(JobSource).filter_by(external_source_id=f"discovery:{provider}", source_type="api").first()
            if source is None:
                source = JobSource(name=f"{provider.title()} — verified discovery", source_type="api",
                                   external_source_id=f"discovery:{provider}")
                db.add(source)
                db.commit()
            jobs = [job.normalized() for job in batch.jobs
                    if job.source == provider and job.status == "open"]
            unverified = sum(job.status in ("unverified", "opportunities") for job in batch.jobs if job.source == provider)
            try:
                result = JobIngestionService(db).collect_from_source(source.id, [profile], jobs)
                results.append({"source": provider, "stage": "import", "status": "partial" if result["failed"] else "completed",
                                "unverified": unverified,
                                **{key: result[key] for key in ("total_fetched", "created", "updated", "skipped", "failed", "contacts_saved")}})
            except Exception:
                db.rollback()
                results.append({"source": provider, "stage": "import", "status": "failed", "error": "Import failed; see backend logs"})
            run.results = list(results)
            db.commit()
        statuses = {r["status"] for r in results}
        run.status = "completed" if statuses == {"completed"} else "partial" if "completed" in statuses or "partial" in statuses else "failed"
        if not results:
            run.error = "No source results supplied; an empty import does not establish successful collection"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return {"run_id": str(run.id), "status": run.status, "results": results}
    except Exception:
        db.rollback()
        run.status, run.error = "failed", "Discovery import failed"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise
