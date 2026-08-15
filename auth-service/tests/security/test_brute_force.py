import pytest
from fastapi.testclient import TestClient
from app.main import app
import uuid

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_developer_brute_force(client):
    # Setup test user
    uid = uuid.uuid4().hex[:8]
    email = f"brute_{uid}@example.com"
    client.post("/api/v1/auth/register", json={
        "username": f"brute_{uid}",
        "email": email,
        "password": "Password123!"
    })

    # Cause 10 failed logins (the burst limit is 10)
    for _ in range(10):
        res = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "WrongPassword!"
        })
        assert res.status_code == 401

    # The 11th failed login should hit the rate limit (429)
    res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "WrongPassword!"
    })
    assert res.status_code == 429
    assert "Too Many Requests" in res.json()["detail"]

    res_correct = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    assert res_correct.status_code == 429

def test_successful_login_clears_ip_block(client):
    import time
    uid = uuid.uuid4().hex[:8]
    email = f"brute2_{uid}@example.com"
    client.post("/api/v1/auth/register", json={
        "username": f"brute2_{uid}",
        "email": email,
        "password": "Password123!"
    })

    # Cause 9 failed logins (use a different IP header to not conflict with previous test if client shares state)
    headers = {"CF-Connecting-IP": "10.0.0.2"}
    for _ in range(9):
        client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "WrongPassword!"
        }, headers=headers)

    # The 10th login is correct. It should succeed and clear the IP block.
    res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!"
    }, headers=headers)
    assert res.status_code == 200
    assert "access_token" in res.json()
    
    # Let the BackgroundTasks finish since TestClient processes them
    time.sleep(0.1)

    # Now we should have a fresh bucket for this IP. We can fail again with a different email.
    res2 = client.post("/api/v1/auth/login", json={
        "email": f"another_{email}",
        "password": "WrongPassword!"
    }, headers=headers)
    assert res2.status_code == 401
