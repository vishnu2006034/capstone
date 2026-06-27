from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    content: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
