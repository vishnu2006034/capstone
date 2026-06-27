from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

class SOPSectionCreate(BaseModel):
    section_number: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=255)
    content: str = Field(..., min_length=1)

class SOPSectionOut(BaseModel):
    id: UUID
    document_id: UUID
    section_number: Optional[str] = None
    title: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class SOPCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    version: str = Field("1.0.0", max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    sections: List[SOPSectionCreate] = Field(default_factory=list)

class SOPOut(BaseModel):
    id: UUID
    title: str
    file_path: Optional[str] = None
    version: str
    department: Optional[str] = None
    uploaded_by: Optional[UUID] = None
    vector_collection_ref: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SOPDetailOut(SOPOut):
    sections: List[SOPSectionOut] = []

    class Config:
        from_attributes = True
