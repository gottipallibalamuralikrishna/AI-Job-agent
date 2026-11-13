
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Job(Base):

    contacts = relationship(
    "JobContact",
    back_populates="job",
    cascade="all, delete-orphan",
    lazy="selectin",
    )
    __tablename__ = "jobs"

    __table_args__ = (
        CheckConstraint(
            "employment_type IS NULL OR employment_type IN "
            "('full_time', 'part_time', 'contract', "
            "'internship', 'freelance', 'temporary')",
            name="ck_jobs_employment_type",
        ),
        CheckConstraint(
            "work_mode IS NULL OR work_mode IN "
            "('remote', 'hybrid', 'onsite')",
            name="ck_jobs_work_mode",
        ),
        CheckConstraint(
            "experience_min IS NULL OR experience_min >= 0",
            name="ck_jobs_experience_min",
        ),
        CheckConstraint(
            "experience_max IS NULL OR experience_max >= 0",
            name="ck_jobs_experience_max",
        ),
        CheckConstraint(
            "salary_min IS NULL OR salary_min >= 0",
            name="ck_jobs_salary_min",
        ),
        CheckConstraint(
            "salary_max IS NULL OR salary_max >= 0",
            name="ck_jobs_salary_max",
        ),
        UniqueConstraint(
            "source_id",
            "external_id",
            name="uq_jobs_source_external_id",
        ),
        Index("ix_jobs_title", "title"),
        Index("ix_jobs_company_name", "company_name"),
        Index("ix_jobs_location", "location"),
        Index("ix_jobs_posted_at", "posted_at"),
        Index("ix_jobs_job_hash", "job_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    company_logo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    employment_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    work_mode: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    experience_min: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    experience_max: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    salary_min: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    salary_max: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    salary_currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    salary_period: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    required_skills: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        nullable=False,
    )

    application_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    job_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    source_message_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    raw_source_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )