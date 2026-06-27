import pytest
import json
from unittest.mock import AsyncMock, patch
from app.models.models import Task, SOPDocument, SOPSection, ComplianceReport, User, Meeting
from app.agents.compliance_agent import audit_task_against_sop

MOCK_AUDIT_JSON = {
    "status": "FAILED",
    "checklist": [
        {"item": "Verify database backup", "passed": False},
        {"item": "Detail rollback script path", "passed": True}
    ],
    "missing_steps": [
        "Task description does not specify backup verification."
    ],
    "compliance_score": 60,
    "risk_level": "HIGH",
    "reasoning": "The proposed task includes a rollback plan but fails to verify the backup, violating SEC-1."
}

@pytest.mark.anyio
async def test_audit_task_against_sop_success(db_session):
    # 1. Setup mock database records
    user = User(name="Auditor User", email="auditor@company.com", role="Admin")
    db_session.add(user)
    db_session.commit()
    
    meeting = Meeting(title="Engineering meeting", status="Uploaded", uploaded_by=user.id)
    db_session.add(meeting)
    db_session.commit()
    
    task = Task(
        meeting_id=meeting.id,
        title="Migrate customer database",
        description="Run migration script to add phone index. Rollback plan: run down migration script.",
        priority="HIGH"
    )
    db_session.add(task)
    db_session.commit()
    
    sop = SOPDocument(
        title="Database Migration Standard",
        version="1.0.0",
        department="DevOps",
        uploaded_by=user.id
    )
    db_session.add(sop)
    db_session.flush()
    
    sec = SOPSection(
        document_id=sop.id,
        section_number="SEC-1",
        title="Backup Verification",
        content="Before executing any SQL DDL/DML, the engineer must verify that an automated backup completes successfully."
    )
    db_session.add(sec)
    db_session.commit()
    
    # 2. Patch the ADK Agent chat call
    mock_chat_response = AsyncMock()
    mock_chat_response.text.return_value = json.dumps(MOCK_AUDIT_JSON)
    
    with patch("google.antigravity.Agent.chat", return_value=mock_chat_response) as mock_chat:
        # Run audit agent pipeline
        report = await audit_task_against_sop(task.id, sop.id, db_session)
        
        # Verify agent was called
        mock_chat.assert_called_once()
        
        # Verify compliance report was stored in DB
        assert report is not None
        assert report.status == "FAILED"
        assert report.compliance_score == 60
        assert report.risk_level == "HIGH"
        assert len(report.checklist) == 2
        assert report.checklist[0]["item"] == "Verify database backup"
        assert report.checklist[0]["passed"] is False
        assert report.missing_steps[0] == "Task description does not specify backup verification."
        
        # Verify task status was updated to Triage because audit failed
        db_task = db_session.query(Task).filter(Task.id == task.id).first()
        assert db_task.status == "Triage"
