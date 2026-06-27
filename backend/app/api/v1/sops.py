import uuid
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
import sqlalchemy as sa
from app.core.events import trigger_sop_uploaded

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError, AppException
from app.api.dependencies import get_current_user
from app.models.models import SOPDocument, SOPSection, User
from app.schemas.sop import SOPCreate, SOPOut, SOPDetailOut
from app.core.audit import log_audit_event

router = APIRouter(prefix="/sops", tags=["Standard Operating Procedures (SOP)"])

@router.post("", response_model=SOPDetailOut, status_code=status.HTTP_201_CREATED)
def create_sop(
    sop_in: SOPCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new SOP Document and saves its individual section clauses.
    """
    # Verify version naming is not duplicates for the same title
    existing = db.query(SOPDocument).filter(
        SOPDocument.title == sop_in.title,
        SOPDocument.version == sop_in.version
    ).first()
    if existing:
        raise AppException(
            code="SOP_VERSION_ALREADY_EXISTS",
            message=f"An SOP with title '{sop_in.title}' and version '{sop_in.version}' is already registered.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 1. Create document
    new_doc = SOPDocument(
        title=sop_in.title,
        version=sop_in.version,
        department=sop_in.department,
        uploaded_by=current_user.id,
        vector_collection_ref=f"sop_{uuid.uuid4().hex[:8]}" # Placeholder vector reference
    )
    db.add(new_doc)
    db.flush()  # Populates new_doc.id

    # 2. Insert sections
    for sec in sop_in.sections:
        new_sec = SOPSection(
            document_id=new_doc.id,
            section_number=sec.section_number,
            title=sec.title,
            content=sec.content
        )
        db.add(new_sec)

    db.commit()
    db.refresh(new_doc)
    
    # Audit log SOP upload
    log_audit_event(db, "SOP_UPLOADED", {"sop_id": str(new_doc.id), "title": new_doc.title}, current_user.id)
    
    # Trigger Ambient Re-audit for this department
    trigger_sop_uploaded(new_doc.id, db, background_tasks)
    
    return new_doc

@router.get("", response_model=List[SOPOut])
def list_sops(
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists and searches SOP documents.
    """
    query = db.query(SOPDocument)

    # Filtering
    if department:
        query = query.filter(SOPDocument.department == department)
    # Searching
    if search:
        query = query.filter(SOPDocument.title.ilike(f"%{search}%"))

    query = query.order_by(SOPDocument.created_at.desc())
    sops = query.offset((page - 1) * limit).limit(limit).all()
    return sops

@router.get("/{sop_id}", response_model=SOPDetailOut)
def get_sop_details(
    sop_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves detailed SOP content including all structural text sections.
    """
    try:
        sop_uuid = uuid.UUID(sop_id)
    except ValueError:
        raise EntityNotFoundError(message=f"SOP Document not found: {sop_id}")

    sop = db.query(SOPDocument).filter(SOPDocument.id == sop_uuid).first()
    if not sop:
        raise EntityNotFoundError(message=f"SOP Document not found: {sop_id}")
    return sop

@router.delete("/{sop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sop(
    sop_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes an SOP Document and cascades deletions to all associated sections.
    """
    try:
        sop_uuid = uuid.UUID(sop_id)
    except ValueError:
        raise EntityNotFoundError(message=f"SOP Document not found: {sop_id}")

    sop = db.query(SOPDocument).filter(SOPDocument.id == sop_uuid).first()
    if not sop:
        raise EntityNotFoundError(message=f"SOP Document not found: {sop_id}")

    db.delete(sop)
    db.commit()
    return None
