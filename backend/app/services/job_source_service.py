
import uuid

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.job_source import JobSource
from app.schemas.job_source import (
    JobSourceCreate,
    JobSourceUpdate,
)


class JobSourceService:

    def __init__(self, db: Session):
        self.db = db

    def _check_duplicate(
        self,
        source_type: str,
        source_url: str | None,
        external_source_id: str | None,
        exclude_id: uuid.UUID | None = None,
    ):
        conditions = []

        if source_url:
            conditions.append(
                func.lower(JobSource.source_url)
                == source_url.strip().lower()
            )

        if external_source_id:
            conditions.append(
                JobSource.external_source_id
                == external_source_id.strip()
            )

        if not conditions:
            return

        query = self.db.query(JobSource).filter(
            JobSource.source_type == source_type,
            or_(*conditions),
        )

        if exclude_id:
            query = query.filter(
                JobSource.id != exclude_id
            )

        if query.first():
            raise HTTPException(
                status_code=409,
                detail="This job source is already registered",
            )

    def create_source(
        self,
        payload: JobSourceCreate,
    ) -> JobSource:

        data = payload.model_dump()

        if data["source_url"]:
            data["source_url"] = data["source_url"].strip()

        if data["external_source_id"]:
            data["external_source_id"] = (
                data["external_source_id"].strip()
            )

        self._check_duplicate(
            source_type=data["source_type"],
            source_url=data["source_url"],
            external_source_id=data["external_source_id"],
        )

        source = JobSource(**data)

        try:
            self.db.add(source)
            self.db.commit()
            self.db.refresh(source)
            return source

        except Exception:
            self.db.rollback()
            raise

    def list_sources(
        self,
        source_type: str | None = None,
    ):

        query = self.db.query(JobSource).filter(
            JobSource.is_active.is_(True)
        )

        if source_type:
            query = query.filter(
                JobSource.source_type == source_type
            )

        return query.order_by(
            JobSource.created_at.desc()
        ).all()

    def get_source(
        self,
        source_id: uuid.UUID,
    ) -> JobSource:

        source = (
            self.db.query(JobSource)
            .filter(
                JobSource.id == source_id,
                JobSource.is_active.is_(True),
            )
            .first()
        )

        if source is None:
            raise HTTPException(
                status_code=404,
                detail="Active job source not found",
            )

        return source

    def update_source(
        self,
        source_id: uuid.UUID,
        payload: JobSourceUpdate,
    ) -> JobSource:

        source = self.get_source(source_id)

        update_data = payload.model_dump(
            exclude_unset=True
        )

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update",
            )

        for field in ("name", "source_type"):
            if field in update_data and update_data[field] is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"{field} cannot be null",
                )

        if "source_url" in update_data:
            value = update_data["source_url"]
            update_data["source_url"] = (
                value.strip() if value else None
            )

        if "external_source_id" in update_data:
            value = update_data["external_source_id"]
            update_data["external_source_id"] = (
                value.strip() if value else None
            )

        new_type = update_data.get(
            "source_type",
            source.source_type,
        )

        new_url = update_data.get(
            "source_url",
            source.source_url,
        )

        new_external_id = update_data.get(
            "external_source_id",
            source.external_source_id,
        )

        self._check_duplicate(
            source_type=new_type,
            source_url=new_url,
            external_source_id=new_external_id,
            exclude_id=source.id,
        )

        for field, value in update_data.items():
            setattr(source, field, value)

        try:
            self.db.commit()
            self.db.refresh(source)
            return source

        except Exception:
            self.db.rollback()
            raise

    def deactivate_source(
        self,
        source_id: uuid.UUID,
    ):

        source = self.get_source(source_id)

        source.is_active = False

        try:
            self.db.commit()

            return {
                "message": "Job source deactivated successfully"
            }

        except Exception:
            self.db.rollback()
            raise
