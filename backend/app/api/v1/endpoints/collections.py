from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.collection_run import CollectionRun
from app.models.user import User
from app.services.collection_service import enqueue_primary

router = APIRouter(prefix="/collections", tags=["Collection"])


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
