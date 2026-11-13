
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SourceType = Literal[
    "telegram",
    "whatsapp",
    "career_page",
    "greenhouse",
    "lever",
    "rss",
    "api",
    "manual",
]


class JobSourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)

    source_type: SourceType

    source_url: str | None = Field(
        default=None,
        max_length=2000,
    )

    external_source_id: str | None = Field(
        default=None,
        max_length=255,
    )


class JobSourceUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    source_type: SourceType | None = None

    source_url: str | None = Field(
        default=None,
        max_length=2000,
    )

    external_source_id: str | None = Field(
        default=None,
        max_length=255,
    )

    is_active: bool | None = None


class JobSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    source_url: str | None
    external_source_id: str | None
    is_active: bool
    last_fetched_at: datetime | None
    created_at: datetime
    updated_at: datetime
