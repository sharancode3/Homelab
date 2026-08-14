import pytest
import io
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_storage_5mb_limit_enforcement(client):
    import uuid
    uid = uuid.uuid4().hex[:8]
    # 1. Login
    res = client.post("/api/v1/auth/register", json={
        "username": f"dev_storage_{uid}",
        "email": f"dev_storage_{uid}@example.com",
        "password": "Password123!"
    })
    res = client.post("/api/v1/auth/login", json={
        "email": f"dev_storage_{uid}@example.com",
        "password": "Password123!"
    })
    token = res.json()["access_token"]
    
    # 2. Create project
    res = client.post("/api/v1/baas/projects/", json={
        "project_name": "Storage Test",
        "project_slug": f"storage-test-{uid}",
        "description": "Test"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = res.json()["project_id"]
    
    # 3. Try to upload 6MB file (should fail)
    # 5MB = 5 * 1024 * 1024 = 5242880 bytes
    large_data = b"a" * (5 * 1024 * 1024 + 1000)
    
    # Mock file with wrong content-length header won't bypass because stream limits it
    res = client.post(
        f"/api/v1/baas/projects/{project_id}/storage",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("large.txt", io.BytesIO(large_data), "text/plain")}
    )
    
    assert res.status_code == 413
    assert "exceeds maximum allowed size" in res.json()["detail"].lower()

def test_storage_path_traversal(client):
    import uuid
    uid = uuid.uuid4().hex[:8]
    res = client.post("/api/v1/auth/register", json={
        "username": f"dev_storage_{uid}",
        "email": f"dev_storage_{uid}@example.com",
        "password": "Password123!"
    })
    res = client.post("/api/v1/auth/login", json={
        "email": f"dev_storage_{uid}@example.com",
        "password": "Password123!"
    })
    token = res.json()["access_token"]
    
    res = client.post("/api/v1/baas/projects/", json={
        "project_name": "Path Traversal Test",
        "project_slug": f"pt-test-{uid}",
        "description": "Test"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = res.json()["project_id"]

    res = client.post(
        f"/api/v1/baas/projects/{project_id}/storage",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("../../../etc/passwd", io.BytesIO(b"malicious"), "text/plain")}
    )
    assert res.status_code == 201
    
    metadata = res.json()
    assert metadata["filename"] == "passwd" # Because of os.path.basename sanitation

def test_email_enumeration_protection(client):
    import uuid
    uid = uuid.uuid4().hex[:8]
    res = client.post("/api/v1/auth/register", json={
        "username": f"dev_storage_{uid}",
        "email": f"dev_storage_{uid}@example.com",
        "password": "Password123!"
    })
    res = client.post("/api/v1/auth/login", json={
        "email": f"dev_storage_{uid}@example.com",
        "password": "Password123!"
    })
    token = res.json()["access_token"]
    
    res = client.post("/api/v1/baas/projects/", json={
        "project_name": "Email Enum Test",
        "project_slug": f"enum-test-{uid}",
        "description": "Test"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = res.json()["project_id"]

    # End-User password reset request for non-existent email
    res = client.post(
        f"/api/v1/baas/projects/{project_id}/auth/reset-password-request",
        json={"email": "nonexistent@example.com"}
    )
    
    assert res.status_code == 200
    assert res.json()["status"] == "success" # Enumeration safe
