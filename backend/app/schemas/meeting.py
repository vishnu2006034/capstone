from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    scheduled_time: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0)

class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, pattern="^(Uploaded|Transcribed|Extracted|Completed)$")
    scheduled_time: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0)

class TranscriptOut(BaseModel):
    id: UUID
    meeting_id: UUID
    raw_text: str
    diarized_conversations: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MeetingOut(BaseModel):
    id: UUID
    title: str
    storage_path: Optional[str] = None
    status: str
    uploaded_by: UUID
    scheduled_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    transcript: Optional[TranscriptOut] = None

    class Config:
        from_attributes = True

class MeetingDetailOut(MeetingOut):
    transcript: Optional[TranscriptOut] = None

    class Config:
        from_attributes = True
