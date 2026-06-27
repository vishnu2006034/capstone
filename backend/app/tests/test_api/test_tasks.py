import pytest

@pytest.fixture
def test_setup(client):
    # Setup a manager user
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin PM",
            "email": "pm@company.com",
            "password": "managerpassword",
            "role": "Manager"
        }
    )
    # Setup developer user
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Dev Alice",
            "email": "alice.dev@company.com",
            "password": "alicepassword",
            "role": "Employee"
        }
    )
    
    # Login PM
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "pm@company.com", "password": "managerpassword"}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create meeting
    meeting_resp = client.post(
        "/api/v1/meetings",
        json={"title": "Sprint Planning"},
        headers=headers
    )
    meeting_id = meeting_resp.json()["id"]
    
    return {
        "headers": headers,
        "meeting_id": meeting_id,
        "developer_email": "alice.dev@company.com"
    }

def test_create_task_and_assign(client, test_setup):
    response = client.post(
        "/api/v1/tasks",
        json={
            "meeting_id": test_setup["meeting_id"],
            "title": "Write API docs",
            "description": "Expose OpenAPI schemas",
            "priority": "HIGH",
            "assignee_emails": [test_setup["developer_email"]]
        },
        headers=test_setup["headers"]
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Write API docs"
    assert data["priority"] == "HIGH"
    assert len(data["assignees"]) == 1
    assert data["assignees"][0]["email"] == test_setup["developer_email"]

def test_list_tasks_filtering_and_search(client, test_setup):
    headers = test_setup["headers"]
    meeting_id = test_setup["meeting_id"]
    
    # Create Task 1
    client.post(
        "/api/v1/tasks",
        json={
            "meeting_id": meeting_id,
            "title": "Setup Docker",
            "description": "Dockerize the postgres service",
            "priority": "CRITICAL"
        },
        headers=headers
    )
    
    # Create Task 2
    client.post(
        "/api/v1/tasks",
        json={
            "meeting_id": meeting_id,
            "title": "Write unit tests",
            "description": "Increase backend coverage",
            "priority": "LOW"
        },
        headers=headers
    )
    
    # 1. Test search query matching description
    search_resp = client.get(
        f"/api/v1/tasks?meeting_id={meeting_id}&search=postgres",
        headers=headers
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert len(search_data) == 1
    assert search_data[0]["title"] == "Setup Docker"
    
    # 2. Test filter by priority
    filter_resp = client.get(
        f"/api/v1/tasks?meeting_id={meeting_id}&priority=LOW",
        headers=headers
    )
    assert filter_resp.status_code == 200
    filter_data = filter_resp.json()
    assert len(filter_data) == 1
    assert filter_data[0]["title"] == "Write unit tests"

def test_add_task_comment(client, test_setup):
    headers = test_setup["headers"]
    
    # Create task
    task_resp = client.post(
        "/api/v1/tasks",
        json={
            "meeting_id": test_setup["meeting_id"],
            "title": "Design ERD"
        },
        headers=headers
    )
    task_id = task_resp.json()["id"]
    
    # Add comment
    comment_resp = client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Please verify user relationships before finalizing"},
        headers=headers
    )
    assert comment_resp.status_code == 201
    data = comment_resp.json()
    assert data["content"] == "Please verify user relationships before finalizing"
    assert data["task_id"] == task_id
    
    # Fetch details and verify comments nested list
    details_resp = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert details_resp.status_code == 200
    details_data = details_resp.json()
    assert len(details_data["comments"]) == 1
    assert details_data["comments"][0]["content"] == "Please verify user relationships before finalizing"

def test_update_task_fields(client, test_setup):
    headers = test_setup["headers"]
    
    # Create task
    task_resp = client.post(
        "/api/v1/tasks",
        json={
            "meeting_id": test_setup["meeting_id"],
            "title": "Old Title"
        },
        headers=headers
    )
    task_id = task_resp.json()["id"]
    
    # Update fields
    update_resp = client.put(
        f"/api/v1/tasks/{task_id}",
        json={
            "title": "Refactored Title",
            "status": "InProgress",
            "priority": "HIGH"
        },
        headers=headers
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["title"] == "Refactored Title"
    assert data["status"] == "InProgress"
    assert data["priority"] == "HIGH"

def test_delete_task(client, test_setup):
    headers = test_setup["headers"]
    
    # Create task
    task_resp = client.post(
        "/api/v1/tasks",
        json={
            "meeting_id": test_setup["meeting_id"],
            "title": "Temporary Task"
        },
        headers=headers
    )
    task_id = task_resp.json()["id"]
    
    # Delete
    del_resp = client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert del_resp.status_code == 204
    
    # Verify deleted
    get_resp = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert get_resp.status_code == 404
