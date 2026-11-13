
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ResumeResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    file_size_bytes: int
    parsing_status: str
    is_primary: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ResumeParseResponse(BaseModel):
    id: UUID
    original_filename: str
    parsing_status: str
    extracted_character_count: int

    model_config = ConfigDict(from_attributes=True)
