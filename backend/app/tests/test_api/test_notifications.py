import pytest
from datetime import datetime, timedelta, timezone
from app.models.models import Task, User, Meeting, Notification, TaskAssignment

@pytest.fixture
def notify_setup(client):
    # Register Manager
    client.post(
        "/api/v1/auth/register",
        json={"name": "PM Manager", "email": "manager@company.com", "password": "mgrpassword", "role": "Manager"}
    )
    
    # Register Employee
    client.post(
        "/api/v1/auth/register",
        json={"name": "Dev Bob", "email": "bob@company.com", "password": "bobpassword", "role": "Employee"}
    )
    
    # Login Manager
    mgr_login = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@company.com", "password": "mgrpassword"}
    )
    mgr_headers = {"Authorization": f"Bearer {mgr_login.json()['access_token']}"}

    # Login Employee
    bob_login = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@company.com", "password": "bobpassword"}
    )
    bob_headers = {"Authorization": f"Bearer {bob_login.json()['access_token']}"}

    return {
        "mgr_headers": mgr_headers,
        "bob_headers": bob_headers,
        "bob_email": "bob@company.com"
    }

def test_list_and_read_notifications(client, db_session, notify_setup):
    # Setup notification in DB for Bob
    bob = db_session.query(User).filter(User.email == "bob@company.com").first()
    notif = Notification(user_id=bob.id, title="Warning", content="Task overdue", is_read=False)
    db_session.add(notif)
    db_session.commit()

    # Get notifications
    get_resp = client.get("/api/v1/notifications", headers=notify_setup["bob_headers"])
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Warning"
    notif_id = data[0]["id"]

    # Mark as read
    read_resp = client.post(f"/api/v1/notifications/{notif_id}/read", headers=notify_setup["bob_headers"])
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True

    # Get notifications again (should be empty since it is read)
    get_resp_2 = client.get("/api/v1/notifications", headers=notify_setup["bob_headers"])
    assert len(get_resp_2.json()) == 0

def test_rbac_escalation_triggers(client, notify_setup):
    # Bob (Employee) should be blocked from triggering escalations
    resp_bob = client.post("/api/v1/notifications/trigger-escalations", headers=notify_setup["bob_headers"])
    assert resp_bob.status_code == 403

    # Manager should succeed
    resp_mgr = client.post("/api/v1/notifications/trigger-escalations", headers=notify_setup["mgr_headers"])
    assert resp_mgr.status_code == 200

def test_escalation_generates_alerts(client, db_session, notify_setup):
    # Setup overdue task (> 24 hours ago)
    manager = db_session.query(User).filter(User.email == "manager@company.com").first()
    bob = db_session.query(User).filter(User.email == "bob@company.com").first()
    
    meeting = Meeting(title="Sprint planning", status="Uploaded", uploaded_by=manager.id)
    db_session.add(meeting)
    db_session.commit()

    yesterday = datetime.now(timezone.utc) - timedelta(days=2)
    task = Task(
        meeting_id=meeting.id,
        title="Deploy index",
        due_date=yesterday,
        status="InProgress"
    )
    db_session.add(task)
    db_session.flush()

    assign = TaskAssignment(task_id=task.id, user_id=bob.id)
    db_session.add(assign)
    db_session.commit()

    # Trigger escalations
    resp = client.post("/api/v1/notifications/trigger-escalations", headers=notify_setup["mgr_headers"])
    assert resp.status_code == 200

    # Verify manager received an escalation notification in DB
    notif = db_session.query(Notification).filter(
        Notification.user_id == manager.id,
        Notification.title.like("ESCALATION%")
    ).first()
    assert notif is not None
    assert "Deploy index" in notif.title
