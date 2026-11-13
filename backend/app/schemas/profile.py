
from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from uuid import UUID


class WorkExperience(BaseModel):
    company: str | None = None
    designation: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    responsibilities: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    graduation_year: int | None = None


class Project(BaseModel):
    name: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    name: str
    issuer: str | None = None
    year: int | None = None


class CandidateProfile(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None

    professional_title: str | None = None
    professional_summary: str | None = None
    total_experience_years: float | None = None

    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)

    work_experience: list[WorkExperience] = Field(
        default_factory=list
    )

    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(
        default_factory=list
    )

    model_config = ConfigDict(extra="forbid")

class ResumeProfileResponse(BaseModel):
    id: UUID
    resume_id: UUID
    profile_data: CandidateProfile
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)