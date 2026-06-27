import pytest
import json
from unittest.mock import AsyncMock, patch
from uuid import UUID
from app.models.models import Meeting, Transcript, User, Task, TaskAssignment
from app.agents.meeting_agent import extract_tasks_from_transcript

MOCK_AGENT_JSON = {
    "tasks": [
        {
            "title": "Implement auth endpoints",
            "description": "Create register and login APIs",
            "assignee_email": "tester@company.com",
            "priority": "HIGH",
            "due_date": "2026-07-01T12:00:00Z",
            "risks": "Database latency issues",
            "dependencies": ["Deploy PostgreSQL"]
        }
    ]
}

@pytest.mark.anyio
async def test_extract_tasks_success(db_session):
    # 1. Setup mock database records
    user = User(
        name="Tester Admin",
        email="tester@company.com",
        role="Admin"
    )
    db_session.add(user)
    db_session.commit()
    
    meeting = Meeting(
        title="Project Kickoff",
        status="Transcribed",
        uploaded_by=user.id
    )
    db_session.add(meeting)
    db_session.commit()
    
    transcript = Transcript(
        meeting_id=meeting.id,
        raw_text="Admin: Hello. We need to implement auth endpoints assigned to tester@company.com by July 1st."
    )
    db_session.add(transcript)
    db_session.commit()
    
    # 2. Patch the Agent.chat call to return our mock JSON
    mock_chat_response = AsyncMock()
    mock_chat_response.text.return_value = json.dumps(MOCK_AGENT_JSON)
    
    with patch("google.antigravity.Agent.chat", return_value=mock_chat_response) as mock_chat:
        # Run agent task extraction
        tasks = await extract_tasks_from_transcript(meeting.id, db_session)
        
        # Verify agent was called
        mock_chat.assert_called_once()
        
        # Verify tasks were persisted to DB
        assert len(tasks) == 1
        db_task = db_session.query(Task).filter(Task.meeting_id == meeting.id).first()
        assert db_task is not None
        assert db_task.title == "Implement auth endpoints"
        assert db_task.priority == "HIGH"
        assert "Risks Identified" in db_task.description
        assert "Dependencies" in db_task.description
        
        # Verify assignment was mapped
        assignment = db_session.query(TaskAssignment).filter(TaskAssignment.task_id == db_task.id).first()
        assert assignment is not None
        assert assignment.user_id == user.id
        
        # Verify meeting status was updated
        db_meeting = db_session.query(Meeting).filter(Meeting.id == meeting.id).first()
        assert db_meeting.status == "Extracted"
