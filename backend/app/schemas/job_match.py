
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class JobSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    company_name: str
    company_logo: str | None = None

    location: str | None = None
    employment_type: str | None = None
    work_mode: str | None = None

    experience_min: int | None = None
    experience_max: int | None = None

    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    salary_period: str | None = None

    description: str | None = None
    required_skills: list[str] = Field(default_factory=list)

    application_url: str | None = None
    posted_at: datetime | None = None
    is_active: bool


class JobMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID

    # Associated job information
    job: JobSummaryResponse

    # Overall matching score
    match_score: float = Field(ge=0, le=100)

    # Skill matching
    matched_skills: list[str]
    missing_skills: list[str]
    candidate_skills: list[str]
    job_skills: list[str]

    matched_skill_count: int
    total_job_skills: int

    decision: str

    # Role classification
    role_family: str | None = None
    candidate_role_family: str | None = None

    # Individual scoring dimensions
    role_match_score: float = Field(default=0, ge=0, le=100)
    skill_match_score: float = Field(default=0, ge=0, le=100)
    experience_match_score: float = Field(default=0, ge=0, le=100)
    responsibility_match_score: float = Field(default=0, ge=0, le=100)

    # Required and preferred skills
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)

    # Experience comparison
    required_experience_years: float | None = None
    candidate_experience_years: float = 0

    # Responsibility matching
    matched_responsibility_categories: list[str] = Field(
        default_factory=list
    )

    # Explanation and rejection reasons
    rejection_reasons: list[str] = Field(default_factory=list)
    match_explanation: str | None = None

    created_at: datetime
    updated_at: datetime
