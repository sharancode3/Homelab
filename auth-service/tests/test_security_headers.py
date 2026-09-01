from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_security_headers_present():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    # Ensure HSTS is NOT present per Phase 23 decision
    assert "Strict-Transport-Security" not in response.headers
