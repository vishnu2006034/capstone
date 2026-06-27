import pytest

@pytest.fixture
def auth_headers(client):
    # Register and login an admin user to get auth headers
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin User",
            "email": "admin@company.com",
            "password": "adminpassword",
            "role": "Admin"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@company.com",
            "password": "adminpassword"
        }
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_sop_with_sections(client, auth_headers):
    response = client.post(
        "/api/v1/sops",
        json={
            "title": "Database Migration Policy",
            "version": "1.2.0",
            "department": "DevOps",
            "sections": [
                {
                    "section_number": "SEC-1",
                    "title": "Backup Prerequisites",
                    "content": "Verify backup completes before running database scripts."
                },
                {
                    "section_number": "SEC-2",
                    "title": "Rollback Plan",
                    "content": "Deployments must specify a rollback strategy."
                }
            ]
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Database Migration Policy"
    assert data["version"] == "1.2.0"
    assert data["department"] == "DevOps"
    assert len(data["sections"]) == 2
    assert data["sections"][0]["title"] == "Backup Prerequisites"

def test_create_duplicate_sop(client, auth_headers):
    payload = {
        "title": "Data Privacy Code",
        "version": "1.0.0",
        "department": "Security",
        "sections": [{"content": "Mask all customer emails."}]
    }
    
    # Ingest first
    resp1 = client.post("/api/v1/sops", json=payload, headers=auth_headers)
    assert resp1.status_code == 201
    
    # Ingest duplicate version
    resp2 = client.post("/api/v1/sops", json=payload, headers=auth_headers)
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "SOP_VERSION_ALREADY_EXISTS"

def test_list_and_search_sops(client, auth_headers):
    # Ingest DevOps SOP
    client.post(
        "/api/v1/sops",
        json={
            "title": "Infrastructure Deploy Plan",
            "version": "1.0.0",
            "department": "DevOps",
            "sections": [{"content": "Use terraform plan."}]
        },
        headers=auth_headers
    )
    # Ingest QA SOP
    client.post(
        "/api/v1/sops",
        json={
            "title": "Testing Guidelines",
            "version": "2.0.0",
            "department": "Quality Assurance",
            "sections": [{"content": "Unit tests must hit 85% coverage."}]
        },
        headers=auth_headers
    )
    
    # 1. Filter by department
    filter_resp = client.get("/api/v1/sops?department=DevOps", headers=auth_headers)
    assert filter_resp.status_code == 200
    filter_data = filter_resp.json()
    assert len(filter_data) == 1
    assert filter_data[0]["title"] == "Infrastructure Deploy Plan"
    
    # 2. Search by title search query
    search_resp = client.get("/api/v1/sops?search=Testing", headers=auth_headers)
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert len(search_data) == 1
    assert search_data[0]["title"] == "Testing Guidelines"

def test_delete_sop_cascades(client, auth_headers):
    create_resp = client.post(
        "/api/v1/sops",
        json={
            "title": "Archived Procedures",
            "version": "1.0.0",
            "department": "DevOps",
            "sections": [{"content": "Temporary instruction text."}]
        },
        headers=auth_headers
    )
    sop_id = create_resp.json()["id"]
    
    # Delete
    del_resp = client.delete(f"/api/v1/sops/{sop_id}", headers=auth_headers)
    assert del_resp.status_code == 204
    
    # Verify details are 404
    get_resp = client.get(f"/api/v1/sops/{sop_id}", headers=auth_headers)
    assert get_resp.status_code == 404
