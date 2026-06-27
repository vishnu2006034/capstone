import pytest
import json
from uuid import UUID
from datetime import datetime
from unittest.mock import MagicMock, patch
from app.models.models import User, Meeting, Transcript, Notification
from app.mcp.server import handle_initialize, handle_list_tools, execute_tool_call

def test_mcp_initialize():
    res = handle_initialize(req_id=42, params={})
    assert res["id"] == 42
    assert res["result"]["serverInfo"]["name"] == "Meeting2Execution-MCP"
    assert "tools" in res["result"]["capabilities"]

def test_mcp_list_tools():
    res = handle_list_tools(req_id=100)
    assert res["id"] == 100
    tools = res["result"]["tools"]
    names = [t["name"] for t in tools]
    assert "postgres_query" in names
    assert "filesystem_read_transcript" in names
    assert "calendar_create_meeting" in names
    assert "notifications_send_alert" in names

def test_mcp_unauthorized_postgres_query():
    # Only SELECT queries are permitted
    args = {"query": "DROP TABLE tasks;"}
    res = execute_tool_call("postgres_query", args)
    assert res["isError"] is True
    assert "Only read-only SELECT" in res["content"][0]["text"]

def test_mcp_postgres_query_select(db_session):
    # Setup user first to satisfy NOT NULL constraint on meetings.uploaded_by
    user = User(name="MCP User", email="mcp.user@company.com", role="Admin")
    db_session.add(user)
    db_session.commit()

    # Setup test meeting to query
    meeting = Meeting(title="Status Check", status="Uploaded", uploaded_by=user.id)
    db_session.add(meeting)
    db_session.commit()

    # Query using SELECT
    args = {"query": "SELECT title FROM meetings WHERE status='Uploaded'"}
    
    # Mock get_db in mcp.server to use our test db_session
    with patch("app.mcp.server.get_db", return_value=db_session):
        res = execute_tool_call("postgres_query", args)
        assert "isError" not in res
        text_val = res["content"][0]["text"]
        rows = json.loads(text_val)
        assert len(rows) == 1
        assert rows[0]["title"] == "Status Check"

def test_mcp_notifications_send_alert(db_session):
    # Setup target user
    user = User(name="Manager User", email="mcp.manager@company.com", role="Manager")
    db_session.add(user)
    db_session.commit()
    
    # Save user_id before session is closed/detached
    user_id = user.id

    args = {
        "email": "mcp.manager@company.com",
        "title": "MCP Warning Alert",
        "message": "Resource constraint detected."
    }

    with patch("app.mcp.server.get_db", return_value=db_session):
        res = execute_tool_call("notifications_send_alert", args)
        assert "isError" not in res
        assert "dispatched" in res["content"][0]["text"]

        # Verify DB notification was created using saved user_id
        notif = db_session.query(Notification).filter(Notification.user_id == user_id).first()
        assert notif is not None
        assert notif.title == "MCP Warning Alert"
