from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.job import Job
from app.models.user import User

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.get("")
def list_applications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return [dict(row) for row in db.execute(text("SELECT job_id, snapshot, applied_at FROM job_applications WHERE user_id=:user ORDER BY applied_at DESC"), {"user": current_user.id}).mappings()]

@router.put("/{job_id}")
def mark_applied(job_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    import json
    snapshot = {"title": job.title, "company_name": job.company_name, "location": job.location, "application_url": job.application_url}
    db.execute(text("INSERT INTO job_applications (user_id, job_id, snapshot) VALUES (:user, :job, CAST(:snapshot AS jsonb)) ON CONFLICT (user_id, job_id) DO NOTHING"), {"user": current_user.id, "job": job.id, "snapshot": json.dumps(snapshot)})
    db.commit()
    return {"status": "applied"}
