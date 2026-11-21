from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.collection_run import CollectionRun
from app.models.resume import Resume
from app.models.resume_profile import ResumeProfile
from app.models.user import User
from app.services.collection_service import enqueue_primary

router = APIRouter(prefix="/collections", tags=["Collection"])


@router.get("/summary")
def collection_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    runs = db.query(CollectionRun).filter_by(user_id=current_user.id)
    latest = runs.order_by(CollectionRun.created_at.desc()).first()
    successful = runs.filter(CollectionRun.status.in_(["completed", "partial"])).order_by(
        CollectionRun.finished_at.desc().nulls_last(),
    ).first()
    ready = db.query(ResumeProfile.id).join(Resume, ResumeProfile.resume_id == Resume.id).filter(
        ResumeProfile.user_id == current_user.id,
        Resume.user_id == current_user.id,
        Resume.is_primary.is_(True),
        Resume.parsing_status == "parsed",
    ).first() is not None
    now = datetime.now(ZoneInfo(settings.collection_timezone))
    next_run = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)

    blocker = None
    if not settings.collection_enabled:
        blocker = "Automatic collection is disabled on this server."
    elif not ready:
        blocker = "Select a primary resume and extract its profile to enable collection."

    return {
        "status": latest.status if latest else None,
        "latest_at": (latest.finished_at or latest.created_at) if latest else None,
        "last_success_at": successful.finished_at if successful else None,
        "new_jobs": sum(result.get("created", 0) for result in (latest.results or [])) if latest else None,
        "source_issues": sum(result.get("status") in {"failed", "partial"} for result in (latest.results or [])) if latest else 0,
        "run_failed": bool(latest and latest.error),
        "blocker": blocker,
        "next_scheduled_at": None if blocker else next_run,
        "timezone": settings.collection_timezone,
    }


@router.post("", status_code=202)
def collect_now(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    run = enqueue_primary(db, current_user.id)
    if run is None:
        raise HTTPException(409, "Select a primary resume, parse it, and extract its profile first")
    db.commit()
    return {"id": run.id, "status": run.status}


@router.get("")
def collection_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    runs = db.query(CollectionRun).filter_by(user_id=current_user.id).order_by(CollectionRun.created_at.desc()).limit(10).all()
    return [{"id": r.id, "resume_id": r.resume_id, "status": r.status,
             "results": r.results, "error": r.error,
             "created_at": r.created_at, "finished_at": r.finished_at} for r in runs]
