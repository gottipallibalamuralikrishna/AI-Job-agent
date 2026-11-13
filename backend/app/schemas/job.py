
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal
from app.schemas.job_contact import JobContactResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


EmploymentType = Literal[
    "full_time",
    "part_time",
    "contract",
    "internship",
    "freelance",
    "temporary",
]

WorkMode = Literal[
    "remote",
    "hybrid",
    "onsite",
]


class JobBase(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)

    company_logo: str | None = None
    location: str | None = Field(default=None, max_length=255)

    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None

    experience_min: int | None = Field(default=None, ge=0)
    experience_max: int | None = Field(default=None, ge=0)

    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, max_length=10)
    salary_period: str | None = Field(default=None, max_length=20)

    description: str | None = None
    required_skills: list[str] = Field(default_factory=list)

    application_url: str | None = None
    posted_at: datetime | None = None
    expires_at: datetime | None = None

    source_message_url: str | None = None
    raw_source_text: str | None = None


class JobCreate(JobBase):
    source_id: uuid.UUID | None = None
    external_id: str | None = Field(default=None, max_length=255)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    company_name: str | None = Field(default=None, min_length=1, max_length=255)

    company_logo: str | None = None
    location: str | None = None

    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None

    experience_min: int | None = Field(default=None, ge=0)
    experience_max: int | None = Field(default=None, ge=0)

    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    salary_period: str | None = None

    description: str | None = None
    required_skills: list[str] | None = None

    application_url: str | None = None
    posted_at: datetime | None = None
    expires_at: datetime | None = None

    is_active: bool | None = None


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID | None
    external_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    contacts: list[JobContactResponse] = Field(
    default_factory=list
    )

class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
