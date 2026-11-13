from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
    job_id: UUID
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
    source_id: UUID


class RecruiterContactResponse(JobContactResponse):
    job: ContactJobSummary


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