import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def assert_no_leakage(text: str):
    lower_text = text.lower()
    # No SQL statements or database identifiers
    assert "select " not in lower_text
    assert "insert into" not in lower_text
    assert "sqlite_" not in lower_text
    assert "_baas_auth" not in lower_text
    
    # No stack traces
    assert "traceback (most recent call last)" not in lower_text
    assert 'file "' not in lower_text
    assert "line " not in lower_text and ", in " not in lower_text
    
    # No paths
    assert "/app/" not in lower_text
    assert "/usr/local" not in lower_text

def test_422_no_leakage(client):
    # Invalid JSON payload
    res = client.post("/api/v1/auth/login", data="not-json")
    assert res.status_code == 422
    assert_no_leakage(res.text)

def test_missing_fields_no_leakage(client):
    res = client.post("/api/v1/auth/login", json={"email": "test@example.com"})
    assert res.status_code == 422
    assert_no_leakage(res.text)

def test_invalid_uuid_no_leakage(client):
    res = client.get("/api/v1/baas/projects/not-a-uuid/tables")
    assert res.status_code in [401, 403, 404, 422] # Depends on routing, but shouldn't leak
    assert_no_leakage(res.text)

def test_malformed_auth_header(client):
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.format"})
    assert res.status_code == 401
    assert_no_leakage(res.text)

def test_malicious_path(client):
    res = client.get("/api/v1/baas/projects/123/tables/sqlite_master")
    assert res.status_code in [401, 422]
    assert_no_leakage(res.text)
