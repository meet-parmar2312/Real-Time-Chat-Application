from fastapi.testclient import TestClient


def test_register_and_login_success(client: TestClient):
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "charlie",
            "email": "charlie@example.com",
            "password": "strongpassword123",
        },
    )
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert reg_data["username"] == "charlie"
    assert reg_data["email"] == "charlie@example.com"
    assert "id" in reg_data

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "charlie@example.com",
            "password": "strongpassword123",
        },
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    token = login_data["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["id"] == reg_data["id"]
    assert me_data["email"] == "charlie@example.com"


def test_register_duplicate_email(client: TestClient, create_test_user):
    create_test_user("user1", "duplicate@example.com")
    res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "user2",
            "email": "duplicate@example.com",
            "password": "password123",
        },
    )
    assert res.status_code == 400
    assert "email address already exists" in res.json()["detail"]


def test_register_duplicate_username(client: TestClient, create_test_user):
    create_test_user("sameusername", "user1@example.com")
    res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "sameusername",
            "email": "user2@example.com",
            "password": "password123",
        },
    )
    assert res.status_code == 400
    assert "username is already taken" in res.json()["detail"]


def test_login_invalid_password(client: TestClient, create_test_user):
    create_test_user("alice", "alice@example.com", "correctpassword")
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrongpassword"},
    )
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


def test_unauthenticated_protected_endpoint(client: TestClient):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401

    res_invalid_token = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token_value"},
    )
    assert res_invalid_token.status_code == 401
