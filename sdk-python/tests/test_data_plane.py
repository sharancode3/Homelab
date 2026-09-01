import pytest
import responses
from homelab_sdk import HomelabClient

@responses.activate
def test_db_insert():
    client = HomelabClient(api_key="pk_live_123")
    responses.add(
        responses.POST,
        "https://localhost:8443/api/v1/baas/projects/p1/data/users",
        json={"id": "row1"},
        status=201
    )
    res = client.db.insert("p1", "users", {"name": "test"})
    assert res["id"] == "row1"
    assert responses.calls[0].request.headers["X-Project-API-Key"] == "pk_live_123"

@responses.activate
def test_db_list():
    client = HomelabClient(api_key="pk_live_123")
    responses.add(
        responses.GET,
        "https://localhost:8443/api/v1/baas/projects/p1/data/users",
        json=[{"data": {"name": "test"}}],
        status=200
    )
    res = client.db.list("p1", "users")
    assert len(res) == 1
    assert responses.calls[0].request.headers["X-Project-API-Key"] == "pk_live_123"

@responses.activate
def test_storage_upload():
    client = HomelabClient(api_key="pk_live_123")
    responses.add(
        responses.POST,
        "https://localhost:8443/api/v1/baas/projects/p1/storage/",
        json={"id": "file1", "filename": "test.txt"},
        status=201
    )
    res = client.storage.upload("p1", "test.txt", b"content")
    assert res["id"] == "file1"
    assert responses.calls[0].request.headers["X-Project-API-Key"] == "pk_live_123"

@responses.activate
def test_storage_download():
    client = HomelabClient(api_key="pk_live_123")
    responses.add(
        responses.GET,
        "https://localhost:8443/api/v1/baas/projects/p1/storage/file1",
        body=b"content",
        status=200
    )
    res = client.storage.download("p1", "file1")
    assert res == b"content"
    assert responses.calls[0].request.headers["X-Project-API-Key"] == "pk_live_123"

@responses.activate
def test_auth_register():
    client = HomelabClient(project_id="p1")
    responses.add(
        responses.POST,
        "https://localhost:8443/api/v1/baas/projects/p1/auth/register",
        json={"id": "eu1", "email": "eu@test.com"},
        status=201
    )
    res = client.auth.register("p1", "eu@test.com", "pass")
    assert res["id"] == "eu1"
    assert "Authorization" not in responses.calls[0].request.headers
    assert "X-Project-API-Key" not in responses.calls[0].request.headers

@responses.activate
def test_auth_me():
    client = HomelabClient(end_user_token="eutoken123")
    responses.add(
        responses.GET,
        "https://localhost:8443/api/v1/baas/projects/p1/auth/me",
        json={"email": "eu@test.com"},
        status=200
    )
    res = client.auth.get_me("p1")
    assert res["email"] == "eu@test.com"
    assert responses.calls[0].request.headers["Authorization"] == "Bearer eutoken123"
