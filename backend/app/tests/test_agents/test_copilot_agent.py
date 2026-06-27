import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone
from app.models.models import Task, User, Meeting, ComplianceReport, TaskAssignment
from app.agents.copilot_agent import ask_manager_copilot

MOCK_COPILOT_ANSWER = (
    "Based on the database state:\n\n"
    "1. **Overdue Tasks**: Task 'Deploy index' is overdue. Assignee is bob@company.com.\n"
    "2. **Overloaded Employees**: bob@company.com is currently assigned to 1 active task."
)

@pytest.mark.anyio
async def test_ask_manager_copilot(db_session):
    # Setup users
    manager = User(name="Manager User", email="mgr@company.com", role="Manager")
    worker = User(name="Bob Dev", email="bob@company.com", role="Employee")
    db_session.add(manager)
    db_session.add(worker)
    db_session.commit()
    
    meeting = Meeting(title="Planning session", status="Uploaded", uploaded_by=manager.id)
    db_session.add(meeting)
    db_session.commit()
    
    # Overdue task
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    task = Task(meeting_id=meeting.id, title="Deploy index", due_date=yesterday, status="InProgress")
    db_session.add(task)
    db_session.flush()
    
    assign = TaskAssignment(task_id=task.id, user_id=worker.id)
    db_session.add(assign)
    db_session.commit()
    
    # Mock ADK agent chat response
    mock_chat_response = AsyncMock()
    mock_chat_response.text.return_value = MOCK_COPILOT_ANSWER
    
    with patch("google.antigravity.Agent.chat", return_value=mock_chat_response) as mock_chat:
        answer = await ask_manager_copilot("What is overdue?", db_session)
        
        # Verify agent was called
        mock_chat.assert_called_once()
        
        # Verify response text matches
        assert "Overdue Tasks" in answer
        assert "bob@company.com" in answer

def test_copilot_api_rbac(client, db_session):
    # Register employee and manager
    client.post(
        "/api/v1/auth/register",
        json={"name": "Emp Bob", "email": "bob.emp@company.com", "password": "password123", "role": "Employee"}
    )
    client.post(
        "/api/v1/auth/register",
        json={"name": "Mgr Jane", "email": "jane.mgr@company.com", "password": "password123", "role": "Manager"}
    )
    
    # Login Employee
    login_emp = client.post("/api/v1/auth/login", json={"email": "bob.emp@company.com", "password": "password123"})
    headers_emp = {"Authorization": f"Bearer {login_emp.json()['access_token']}"}
    
    # Login Manager
    login_mgr = client.post("/api/v1/auth/login", json={"email": "jane.mgr@company.com", "password": "password123"})
    headers_mgr = {"Authorization": f"Bearer {login_mgr.json()['access_token']}"}
    
    # Query copilot as Employee -> should be 403 Forbidden
    resp_emp = client.post(
        "/api/v1/copilot/query",
        json={"query": "Who is overloaded?"},
        headers=headers_emp
    )
    assert resp_emp.status_code == 403
    
    # Query copilot as Manager -> should succeed (mocking the agent call)
    mock_chat_response = AsyncMock()
    mock_chat_response.text.return_value = "Manager response here"
    
    with patch("google.antigravity.Agent.chat", return_value=mock_chat_response):
        resp_mgr = client.post(
            "/api/v1/copilot/query",
            json={"query": "Who is overloaded?"},
            headers=headers_mgr
        )
        assert resp_mgr.status_code == 200
        assert resp_mgr.json()["answer"] == "Manager response here"
