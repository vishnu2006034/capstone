import pytest

@pytest.fixture
def auth_headers(client):
    # Register and login a user to get authorization headers
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane PM",
            "email": "jane.pm@company.com",
            "password": "securepassword",
            "role": "Manager"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "jane.pm@company.com",
            "password": "securepassword"
        }
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_meeting(client, auth_headers):
    response = client.post(
        "/api/v1/meetings",
        json={
            "title": "Weekly Sync",
            "duration_seconds": 1800
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Weekly Sync"
    assert data["status"] == "Uploaded"
    assert "id" in data

def test_list_meetings(client, auth_headers):
    # Create one first
    client.post(
        "/api/v1/meetings",
        json={"title": "Sprint Planning"},
        headers=auth_headers
    )
    
    response = client.get("/api/v1/meetings", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "Sprint Planning"

def test_meeting_details_with_transcript(client, auth_headers):
    # Create meeting
    create_resp = client.post(
        "/api/v1/meetings",
        json={"title": "Design Session"},
        headers=auth_headers
    )
    meeting_id = create_resp.json()["id"]

    # Details before transcript
    details_resp = client.get(f"/api/v1/meetings/{meeting_id}", headers=auth_headers)
    assert details_resp.status_code == 200
    assert details_resp.json()["transcript"] is None

    # Upload transcript
    transcript_resp = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-transcript",
        json={"raw_text": "Alice: Hello Bob. Bob: Hi Alice. We need to push the server update."},
        headers=auth_headers
    )
    assert transcript_resp.status_code == 200
    assert transcript_resp.json()["raw_text"] == "Alice: Hello Bob. Bob: Hi Alice. We need to push the server update."

    # Details after transcript
    details_resp2 = client.get(f"/api/v1/meetings/{meeting_id}", headers=auth_headers)
    assert details_resp2.status_code == 200
    data = details_resp2.json()
    assert data["status"] in ["Transcribed", "Extracted"]
    assert data["transcript"] is not None
    assert data["transcript"]["raw_text"].startswith("Alice:")

def test_update_meeting(client, auth_headers):
    create_resp = client.post(
        "/api/v1/meetings",
        json={"title": "Retro"},
        headers=auth_headers
    )
    meeting_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/meetings/{meeting_id}",
        json={"title": "Q2 Retrospective", "status": "Completed"},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Q2 Retrospective"
    assert data["status"] == "Completed"

def test_delete_meeting(client, auth_headers):
    create_resp = client.post(
        "/api/v1/meetings",
        json={"title": "Triage Meeting"},
        headers=auth_headers
    )
    meeting_id = create_resp.json()["id"]

    # Delete
    del_resp = client.delete(f"/api/v1/meetings/{meeting_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Confirm deleted
    get_resp = client.get(f"/api/v1/meetings/{meeting_id}", headers=auth_headers)
    assert get_resp.status_code == 404
