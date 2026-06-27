from typing import List
from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError, AppException
from app.api.dependencies import get_current_user
from app.models.models import Meeting, Transcript, User
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingOut, MeetingDetailOut, TranscriptOut

router = APIRouter(prefix="/meetings", tags=["Meetings"])

@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
def create_meeting(
    meeting_in: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new meeting record under the acting user's profile.
    """
    new_meeting = Meeting(
        title=meeting_in.title,
        status="Uploaded",
        uploaded_by=current_user.id,
        scheduled_time=meeting_in.scheduled_time,
        duration_seconds=meeting_in.duration_seconds
    )
    db.add(new_meeting)
    db.commit()
    db.refresh(new_meeting)
    return new_meeting

@router.get("", response_model=List[MeetingOut])
def list_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists all meeting records.
    """
    # In an enterprise dashboard, we might filter by user, but let's return all meetings in the project.
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).all()
    return meetings

@router.get("/{meeting_id}", response_model=MeetingDetailOut)
def get_meeting_details(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a detailed meeting record including its associated transcript.
    """
    import uuid
    try:
        meeting_uuid = uuid.UUID(meeting_id)
    except ValueError:
        raise EntityNotFoundError(message=f"Meeting not found: {meeting_id}")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid).first()
    if not meeting:
        raise EntityNotFoundError(message=f"Meeting not found: {meeting_id}")
    return meeting

@router.put("/{meeting_id}", response_model=MeetingOut)
def update_meeting(
    meeting_id: str,
    meeting_in: MeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates meeting fields.
    """
    import uuid
    try:
        meeting_uuid = uuid.UUID(meeting_id)
    except ValueError:
        raise EntityNotFoundError(message=f"Meeting not found: {meeting_id}")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid).first()
    if not meeting:
        raise EntityNotFoundError(message=f"Meeting not found: {meeting_id}")

    # Apply changes
    update_data = meeting_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meeting, field, value)

    db.commit()
    db.refresh(meeting)
    return meeting

@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a meeting and cascades deletions (transcripts, tasks, etc.).
    """
    import uuid
    try:
        meeting_uuid = uuid.UUID(meeting_id)
    except ValueError:
        raise EntityNotFoundError(message=f"Meeting not found: {meeting_id}")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid).first()
    if not meeting:
        raise EntityNotFoundError(message=f"Meeting not found: {meeting_id}")

    db.delete(meeting)
    db.commit()
    return None

@router.post("/{meeting_id}/upload-transcript", response_model=TranscriptOut)
def upload_transcript(
    meeting_id: str,
    raw_text: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a meeting transcript and links it to the meeting.
    Updates the meeting status to 'Transcribed'.
    """
    import uuid
    try:
        meeting_uuid = uuid.UUID(meeting_id)
    except ValueError:
        raise EntityNotFoundError(message=f"Meeting not found: {meeting_id}")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid).first()
    if not meeting:
        raise EntityNotFoundError(message=f"Meeting not found: {meeting_id}")

    # Check if a transcript already exists for this meeting
    existing_transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting_uuid).first()
    if existing_transcript:
        existing_transcript.raw_text = raw_text
        db.add(existing_transcript)
    else:
        new_transcript = Transcript(
            meeting_id=meeting_uuid,
            raw_text=raw_text
        )
        db.add(new_transcript)

    # Set meeting status to Transcribed
    meeting.status = "Transcribed"
    db.add(meeting)
    
    db.commit()
    
    # Reload and return transcript
    transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting_uuid).first()
    return transcript
