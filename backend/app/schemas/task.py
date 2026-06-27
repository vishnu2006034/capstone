from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr
from app.schemas.auth import UserOut

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)

class CommentOut(BaseModel):
    id: UUID
    task_id: UUID
    user_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    meeting_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: str = Field("MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    due_date: Optional[datetime] = None
    assignee_emails: List[EmailStr] = Field(default_factory=list)

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    status: Optional[str] = Field(None, pattern="^(Extracted|Approved|Triage|Provisioned|InProgress|Done)$")
    due_date: Optional[datetime] = None
    external_ticket_ref: Optional[str] = None

class TaskOut(BaseModel):
    id: UUID
    meeting_id: UUID
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    due_date: Optional[datetime] = None
    external_ticket_ref: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # We can serialize assignees and comments
    assignees: List[UserOut] = []
    comments: List[CommentOut] = []

    class Config:
        from_attributes = True
