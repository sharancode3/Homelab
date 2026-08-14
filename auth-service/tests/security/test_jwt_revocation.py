import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_developer_logout_and_revocation(client):
    import uuid
    uid = uuid.uuid4().hex
    # 1. Register and Login a Developer
    res = client.post("/api/v1/auth/register", json={
        "username": "dev_revoked",
        "email": "dev_revoked@example.com",
        "password": "Password123!"
    })
    
    res = client.post("/api/v1/auth/login", json={
        "email": "dev_revoked@example.com",
        "password": "Password123!"
    })
    token = res.json()["access_token"]
    
    res = client.post("/api/v1/baas/projects/", json={
        "project_name": "Test Auth",
        "project_slug": f"test-auth-{uid}",
        "description": "Test"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200 or res.status_code == 201
    
    # 3. Logout
    res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204
    
    # 4. Try to access again -> should be 401
    res = client.post("/api/v1/baas/projects/", json={
        "project_name": "Test Auth 2",
        "project_slug": f"test-auth-2-{uid}",
        "description": "Test"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Token has been revoked"

def test_end_user_logout_and_revocation(client):
    import uuid
    uid = uuid.uuid4().hex
    # 1. Create a project
    res = client.post("/api/v1/auth/login", json={
        "email": "dev_revoked@example.com",
        "password": "Password123!"
    })
    token = res.json()["access_token"]
    
    res = client.post("/api/v1/baas/projects/", json={
        "project_name": f"Revocation Test {uid}",
        "project_slug": f"revocation-test-{uid}",
        "description": "Test"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = res.json()["project_id"]
    
    # 2. Register and Login an End User
    res = client.post(f"/api/v1/baas/projects/{project_id}/auth/register", json={
        "email": "eu_revoked@example.com",
        "password": "Password123!"
    })
    
    res = client.post(f"/api/v1/baas/projects/{project_id}/auth/login", json={
        "email": "eu_revoked@example.com",
        "password": "Password123!"
    })
    eu_token = res.json()["access_token"]
    
    # 3. Access a protected endpoint
    res = client.get(f"/api/v1/baas/projects/{project_id}/auth/me", headers={"Authorization": f"Bearer {eu_token}"})
    assert res.status_code == 200
    
    # 4. Logout
    res = client.post(f"/api/v1/baas/projects/{project_id}/auth/logout", headers={"Authorization": f"Bearer {eu_token}"})
    assert res.status_code == 204
    
    # 5. Try to access again -> should be 401
    res = client.get(f"/api/v1/baas/projects/{project_id}/auth/me", headers={"Authorization": f"Bearer {eu_token}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Token has been revoked"
