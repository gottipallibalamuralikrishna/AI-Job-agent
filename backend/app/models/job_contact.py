
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JobContact(Base):
    __tablename__ = "job_contacts"

    __table_args__ = (
        CheckConstraint(
            "contact_type IN "
            "('email', 'phone', 'application_url', "
            "'linkedin', 'telegram', 'website')",
            name="ck_job_contacts_contact_type",
        ),
        UniqueConstraint(
            "job_id",
            "contact_type",
            "contact_value",
            name="uq_job_contacts_job_type_value",
        ),
        Index("ix_job_contacts_job_id", "job_id"),
        Index("ix_job_contacts_contact_type", "contact_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    contact_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    contact_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    contact_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job = relationship(
        "Job",
        back_populates="contacts",
    )
