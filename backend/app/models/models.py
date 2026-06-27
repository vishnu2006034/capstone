import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text, Integer, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    role = Column(String(50), nullable=False, default="Developer")  # Manager, Developer, Auditor, Admin
    active_directory_id = Column(String(255), nullable=True, unique=True, index=True)
    hashed_password = Column(String(255), nullable=True)

    # Relationships
    meetings_uploaded = relationship("Meeting", back_populates="uploader", cascade="all, delete-orphan")
    tasks_assigned = relationship("TaskAssignment", back_populates="assignee", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    sop_documents = relationship("SOPDocument", back_populates="uploader", cascade="all, delete-orphan")


class Meeting(Base, TimestampMixin):
    __tablename__ = "meetings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    storage_path = Column(String(1024), nullable=True)
    status = Column(String(50), nullable=False, default="Uploaded")  # Uploaded, Transcribed, Extracted, Completed
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Relationships
    uploader = relationship("User", back_populates="meetings_uploaded")
    participants = relationship("MeetingParticipant", back_populates="meeting", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="meeting", cascade="all, delete-orphan")
    transcript = relationship("Transcript", back_populates="meeting", uselist=False, cascade="all, delete-orphan")


class Transcript(Base, TimestampMixin):
    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    raw_text = Column(Text, nullable=False)
    diarized_conversations = Column(JSON, nullable=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="transcript")


class MeetingParticipant(Base, TimestampMixin):
    __tablename__ = "meeting_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)  # Speaker label from transcript
    email = Column(String(255), nullable=True)   # Resolved corporate email

    # Relationships
    meeting = relationship("Meeting", back_populates="participants")
    user = relationship("User")


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(50), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(50), nullable=False, default="Extracted") # Extracted, Approved, Triage, Provisioned, InProgress, Done
    due_date = Column(DateTime(timezone=True), nullable=True)
    external_ticket_ref = Column(String(255), nullable=True, index=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="tasks")
    assignments = relationship("TaskAssignment", back_populates="task", cascade="all, delete-orphan")
    compliance_reports = relationship("ComplianceReport", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")


class TaskAssignment(Base, TimestampMixin):
    __tablename__ = "task_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    task = relationship("Task", back_populates="assignments")
    assignee = relationship("User", back_populates="tasks_assigned")


class SOPDocument(Base, TimestampMixin):
    __tablename__ = "sop_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=True)
    version = Column(String(50), nullable=False, default="1.0.0")
    department = Column(String(100), nullable=True, index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    vector_collection_ref = Column(String(255), nullable=True)

    # Relationships
    uploader = relationship("User", back_populates="sop_documents")
    sections = relationship("SOPSection", back_populates="document", cascade="all, delete-orphan")


class SOPSection(Base, TimestampMixin):
    __tablename__ = "sop_sections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("sop_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    section_number = Column(String(50), nullable=True)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)

    # Relationships
    document = relationship("SOPDocument", back_populates="sections")


class ComplianceReport(Base, TimestampMixin):
    __tablename__ = "compliance_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="PASSED")  # PASSED, WARNING, FAILED
    reasoning_trace = Column(Text, nullable=True)

    # Relationships
    task = relationship("Task", back_populates="compliance_reports")


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)

    # Relationships
    user = relationship("User", back_populates="notifications")


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., MEETING_UPLOAD, TASK_PROVISION, SOP_UPDATE
    details = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")


class TaskComment(Base, TimestampMixin):
    __tablename__ = "task_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User")
