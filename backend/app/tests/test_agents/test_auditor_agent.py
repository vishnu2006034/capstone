import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from app.models.models import Task, TaskAssignment, User, Meeting, Notification, AuditLog, ComplianceReport
from app.agents.auditor_agent import run_operations_audit

MOCK_AUDIT_LOG_JSON = {
    "alerts": [
        {
            "assignee_email": "dev.bob@company.com",
            "title": "[ALERT] Task Overdue",
            "message": "Task 'Write unit tests' has passed its deadline and is incomplete.",
            "severity": "CRITICAL"
        }
    ],
    "violations_summary": "1 overdue task detected for dev.bob@company.com.",
    "remediation_plan": "Follow up with dev.bob@company.com immediately to resolve blockages."
}

@pytest.mark.anyio
async def test_run_operations_audit_success(db_session):
    # 1. Setup mock database records
    manager = User(name="Manager User", email="pm.manager@company.com", role="Manager")
    dev = User(name="Developer Bob", email="dev.bob@company.com", role="Employee")
    db_session.add(manager)
    db_session.add(dev)
    db_session.commit()
    
    meeting = Meeting(title="Sprint Plan", status="Uploaded", uploaded_by=manager.id)
    db_session.add(meeting)
    db_session.commit()
    
    # Overdue task (due date is yesterday)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    overdue_task = Task(
        meeting_id=meeting.id,
        title="Write unit tests",
        description="Cover task management routes",
        priority="MEDIUM",
        status="InProgress",
        due_date=yesterday
    )
    db_session.add(overdue_task)
    db_session.flush()
    
    # Assign to developer Bob
    assignment = TaskAssignment(task_id=overdue_task.id, user_id=dev.id)
    db_session.add(assignment)
    db_session.commit()
    
    # 2. Patch the ADK Agent chat call
    mock_chat_response = AsyncMock()
    mock_chat_response.text.return_value = json.dumps(MOCK_AUDIT_LOG_JSON)
    
    with patch("google.antigravity.Agent.chat", return_value=mock_chat_response) as mock_chat:
        # Run operations audit pipeline
        result = await run_operations_audit(db_session)
        
        # Verify agent was called
        mock_chat.assert_called_once()
        
        # Verify result output
        assert result["status"] == "SUCCESS"
        assert result["issues_detected"] == 1
        assert result["alerts_sent"] == 1
        
        # Verify notification was stored for Bob
        notify = db_session.query(Notification).filter(Notification.user_id == dev.id).first()
        assert notify is not None
        assert notify.title == "[ALERT] Task Overdue"
        assert "incomplete" in notify.content
        
        # Verify Audit Log was recorded
        log = db_session.query(AuditLog).filter(AuditLog.action == "OPERATIONS_AUDIT_RUN").first()
        assert log is not None
        assert log.details["violations_count"] == 0  # no failed compliance reports in db
        assert log.details["overdue_count"] == 1
        assert log.details["remediation_plan"].startswith("Follow up")
