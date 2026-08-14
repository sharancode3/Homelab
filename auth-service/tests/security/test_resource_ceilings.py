import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_enforce_50_tables_limit(client):
    import uuid
    uid = uuid.uuid4().hex
    # 1. Login
    res = client.post("/api/v1/auth/register", json={
        "username": "dev_ceilings",
        "email": "dev_ceilings@example.com",
        "password": "Password123!"
    })
    res = client.post("/api/v1/auth/login", json={
        "email": "dev_ceilings@example.com",
        "password": "Password123!"
    })
    token = res.json()["access_token"]
    
    # 2. Create project
    res = client.post("/api/v1/baas/projects/", json={
        "project_name": "Ceilings Test",
        "project_slug": f"ceilings-test-{uid}",
        "description": "Test"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = res.json()["project_id"]
    
    # 3. Create 50 tables
    for i in range(50):
        res = client.post(f"/api/v1/baas/projects/{project_id}/tables", json={
            "name": f"test_table_{i}",
            "columns": {"col1": "TEXT"}
        }, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 201

    # 4. 51st table should fail
    res = client.post(f"/api/v1/baas/projects/{project_id}/tables", json={
        "name": f"test_table_51",
        "columns": {"col1": "TEXT"}
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422
    assert "Cannot exceed 50 tables" in res.json()["detail"]

def test_enforce_50_columns_limit(client):
    import uuid
    uid = uuid.uuid4().hex
    res = client.post("/api/v1/auth/login", json={
        "email": "dev_ceilings@example.com",
        "password": "Password123!"
    })
    token = res.json()["access_token"]
    
    res = client.post("/api/v1/baas/projects/", json={
        "project_name": "Ceilings Test 2",
        "project_slug": f"ceilings-test-2-{uid}",
        "description": "Test"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = res.json()["project_id"]
    
    columns = {f"col_{i}": "TEXT" for i in range(51)}
    
    res = client.post(f"/api/v1/baas/projects/{project_id}/tables", json={
        "name": "too_many_cols",
        "columns": columns
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422
    assert "Cannot exceed 50 columns" in res.json()["detail"]

def test_long_identifier_rejected(client):
    import uuid
    uid = uuid.uuid4().hex
    res = client.post("/api/v1/auth/login", json={
        "email": "dev_ceilings@example.com",
        "password": "Password123!"
    })
    token = res.json()["access_token"]
    
    res = client.post("/api/v1/baas/projects/", json={
        "project_name": "Ceilings Test 3",
        "project_slug": f"ceilings-test-3-{uid}",
        "description": "Test"
    }, headers={"Authorization": f"Bearer {token}"})
    project_id = res.json()["project_id"]
    
    long_name = "a" * 65
    res = client.post(f"/api/v1/baas/projects/{project_id}/tables", json={
        "name": long_name,
        "columns": {"col1": "TEXT"}
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422
    assert "String should match pattern" in res.json()["detail"][0]["msg"]
