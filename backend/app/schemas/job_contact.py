from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


ContactType = Literal[
    "email",
    "phone",
    "application_url",
    "linkedin",
    "telegram",
    "website",
]


class JobContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID | None
    contact_type: ContactType
    contact_value: str
    contact_name: str | None = None
    is_primary: bool
    is_verified: bool
    created_at: datetime


class ContactJobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    company_name: str
    location: str | None = None
    application_url: str | None = None
    source_id: UUID | None = None


class RecruiterContactResponse(JobContactResponse):
    job: ContactJobSummary

    @model_validator(mode="before")
    @classmethod
    def include_retained_job(cls, value):
        if not isinstance(value, dict) and value.job is None:
            return {**{name: getattr(value, name) for name in JobContactResponse.model_fields},
                    "job": value.job_snapshot}
        return value


class RecruiterContactListResponse(BaseModel):
    items: list[RecruiterContactResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RecruiterContactStatsResponse(BaseModel):
    total_contacts: int
    total_emails: int
    total_phones: int
    total_linkedin: int
    total_telegram: int
    total_websites: int
    total_application_urls: int
    jobs_with_contacts: int
