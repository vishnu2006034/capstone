import pytest
import json
import sqlalchemy as sa
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone
from app.models.models import Task, User, Meeting, Notification, SOPDocument, SOPSection, ComplianceReport, TaskAssignment
from app.core.events import (
    trigger_task_assigned,
    trigger_task_completed,
    trigger_compliance_violation,
    trigger_deadline_approaching,
    handle_meeting_uploaded,
    handle_sop_uploaded
)

# Mock details
MOCK_TASKS_JSON = {
    "tasks": [
        {
            "title": "Config database pool",
            "description": "Configure pool size and leak detection.",
            "assignee_email": "bob@company.com",
            "priority": "HIGH"
        }
    ]
}

MOCK_AUDIT_JSON = {
    "status": "FAILED",
    "checklist": [
        {"item": "Backup verified", "passed": False}
    ],
    "missing_steps": ["No backup verification details"],
    "compliance_score": 40,
    "risk_level": "CRITICAL",
    "reasoning": "Missing backup parameters."
}

@pytest.mark.anyio
async def test_trigger_task_assigned(db_session):
    # Setup user and task
    user = User(name="Worker User", email="worker@company.com", role="Employee")
    db_session.add(user)
    db_session.commit()
    
    meeting = Meeting(title="Engineering Sync", status="Uploaded", uploaded_by=user.id)
    db_session.add(meeting)
    db_session.commit()
    
    task = Task(meeting_id=meeting.id, title="Refactor core components")
    db_session.add(task)
    db_session.commit()
    
    # Trigger task assigned
    trigger_task_assigned(task.id, user.id, db_session)
    
    # Verify notification created
    notify = db_session.query(Notification).filter(Notification.user_id == user.id).first()
    assert notify is not None
    assert "assigned" in notify.content
    assert notify.title == "New Task Assignment"

@pytest.mark.anyio
async def test_trigger_task_completed(db_session):
    # Setup users
    manager = User(name="Manager User", email="manager@company.com", role="Manager")
    worker = User(name="Worker User", email="worker@company.com", role="Employee")
    db_session.add(manager)
    db_session.add(worker)
    db_session.commit()
    
    meeting = Meeting(title="Weekly Sprint Sync", status="Uploaded", uploaded_by=manager.id)
    db_session.add(meeting)
    db_session.commit()
    
    task = Task(meeting_id=meeting.id, title="Implement triggers")
    db_session.add(task)
    db_session.commit()
    
    # Trigger task completed
    trigger_task_completed(task.id, db_session)
    
    # Verify manager was notified
    notify = db_session.query(Notification).filter(Notification.user_id == manager.id).first()
    assert notify is not None
    assert "completed" in notify.content

@pytest.mark.anyio
async def test_trigger_compliance_violation(db_session):
    # Setup manager and compliance officer users
    manager = User(name="Manager User", email="manager@company.com", role="Manager")
    officer = User(name="Compliance Officer", email="compliance@company.com", role="Compliance Officer")
    db_session.add(manager)
    db_session.add(officer)
    db_session.commit()
    
    meeting = Meeting(title="Sync Meeting", status="Uploaded", uploaded_by=manager.id)
    db_session.add(meeting)
    db_session.commit()
    
    task = Task(meeting_id=meeting.id, title="Production deployment")
    db_session.add(task)
    db_session.commit()
    
    report = ComplianceReport(
        task_id=task.id,
        status="FAILED",
        compliance_score=30,
        risk_level="CRITICAL"
    )
    db_session.add(report)
    db_session.commit()
    
    # Trigger compliance violation
    trigger_compliance_violation(report.id, db_session)
    
    # Verify both manager and compliance officer were notified
    notif_manager = db_session.query(Notification).filter(Notification.user_id == manager.id).first()
    notif_officer = db_session.query(Notification).filter(Notification.user_id == officer.id).first()
    assert notif_manager is not None
    assert notif_officer is not None
    assert "SOP Compliance Breach" in notif_officer.title

@pytest.mark.anyio
async def test_trigger_deadline_approaching(db_session):
    # Setup worker user
    worker = User(name="Worker User", email="worker@company.com", role="Employee")
    db_session.add(worker)
    db_session.commit()
    
    meeting = Meeting(title="Sync Meeting", status="Uploaded", uploaded_by=worker.id)
    db_session.add(meeting)
    db_session.commit()
    
    # Create task due in 2 hours
    due_time = datetime.now(timezone.utc) + timedelta(hours=2)
    task = Task(
        meeting_id=meeting.id,
        title="Urgent DDL fix",
        due_date=due_time,
        status="InProgress"
    )
    db_session.add(task)
    db_session.flush()
    
    assignment = TaskAssignment(task_id=task.id, user_id=worker.id)
    db_session.add(assignment)
    db_session.commit()
    
    # Trigger scanner
    trigger_deadline_approaching(db_session)
    
    # Verify notification created
    notify = db_session.query(Notification).filter(Notification.user_id == worker.id).first()
    assert notify is not None
    assert notify.title == "[URGENT] Deadline Approaching"

@pytest.mark.anyio
@patch("google.antigravity.Agent.chat")
async def test_handle_meeting_uploaded_background(mock_chat, db_session):
    # Setup database records
    user = User(name="Tester Admin", email="bob@company.com", role="Admin")
    db_session.add(user)
    db_session.commit()
    
    meeting = Meeting(title="Sprint kickoff", status="Transcribed", uploaded_by=user.id)
    db_session.add(meeting)
    db_session.commit()
    
    from app.models.models import Transcript
    transcript = Transcript(
        meeting_id=meeting.id,
        raw_text="Bob: I will configure the database pool."
    )
    db_session.add(transcript)
    db_session.commit()
    
    sop = SOPDocument(title="Engineering Guidelines", version="1.0.0", department="Engineering", uploaded_by=user.id)
    db_session.add(sop)
    db_session.flush()
    
    sec = SOPSection(document_id=sop.id, content="Backup guidelines.")
    db_session.add(sec)
    db_session.commit()
    
    # Setup mock agent chats (MIA extract, then SCA audit)
    mock_resp1 = AsyncMock()
    mock_resp1.text.return_value = json.dumps(MOCK_TASKS_JSON)
    
    mock_resp2 = AsyncMock()
    mock_resp2.text.return_value = json.dumps(MOCK_AUDIT_JSON)
    
    mock_chat.side_effect = [mock_resp1, mock_resp2]
    
    # Trigger background meeting uploaded handler
    await handle_meeting_uploaded(meeting.id, db_session)
    
    # Verify tasks extracted
    db_task = db_session.query(Task).filter(Task.meeting_id == meeting.id).first()
    assert db_task is not None
    assert db_task.title == "Config database pool"
    
    # Verify compliance check run and failed report recorded
    report = db_session.query(ComplianceReport).filter(ComplianceReport.task_id == db_task.id).first()
    assert report is not None
    assert report.status == "FAILED"
    assert report.risk_level == "CRITICAL"
    
    # Verify task changed to Triage
    assert db_task.status == "Triage"
