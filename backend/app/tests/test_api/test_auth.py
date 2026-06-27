def test_register_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@company.com",
            "password": "strongpassword123",
            "role": "Manager"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["email"] == "jane@company.com"
    assert data["role"] == "Manager"
    assert "id" in data

def test_register_duplicate_email(client):
    # Register first time
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane Doe",
            "email": "jane@company.com",
            "password": "strongpassword123",
            "role": "Manager"
        }
    )
    # Register duplicate
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane Shadow",
            "email": "jane@company.com",
            "password": "strongpassword123",
            "role": "Employee"
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "EMAIL_ALREADY_TAKEN"

def test_login_successful(client):
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Bob Smith",
            "email": "bob@company.com",
            "password": "secretpassword",
            "role": "Employee"
        }
    )
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "bob@company.com",
            "password": "secretpassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_failed_password(client):
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Bob Smith",
            "email": "bob@company.com",
            "password": "secretpassword",
            "role": "Employee"
        }
    )
    # Login wrong pwd
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "bob@company.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"

def test_get_current_user_profile(client):
    # Register and login
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Alice Cooper",
            "email": "alice@company.com",
            "password": "alicepassword",
            "role": "Compliance Officer"
        }
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@company.com",
            "password": "alicepassword"
        }
    )
    access_token = login_resp.json()["access_token"]
    
    # Get profile
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Alice Cooper"
    assert data["role"] == "Compliance Officer"

def test_get_profile_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
