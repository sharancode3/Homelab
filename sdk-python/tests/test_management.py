import pytest
import responses
from homelab_sdk import HomelabClient

@responses.activate
def test_admin_register():
    client = HomelabClient()
    responses.add(
        responses.POST,
        "https://localhost:8443/api/v1/auth/register",
        json={"user_id": "u1", "email": "test@test.com"},
        status=201
    )
    res = client.admin.register("test@test.com", "test", "pass")
    assert res["user_id"] == "u1"
    assert "Authorization" not in responses.calls[0].request.headers

@responses.activate
def test_admin_me():
    client = HomelabClient(developer_token="dev123")
    responses.add(
        responses.GET,
        "https://localhost:8443/api/v1/auth/me",
        json={"email": "test@test.com"},
        status=200
    )
    res = client.admin.get_me()
    assert res["email"] == "test@test.com"
    assert responses.calls[0].request.headers["Authorization"] == "Bearer dev123"

@responses.activate
def test_projects_create():
    client = HomelabClient(developer_token="dev123")
    responses.add(
        responses.POST,
        "https://localhost:8443/api/v1/baas/projects/",
        json={"id": "p1", "name": "Test"},
        status=201
    )
    res = client.projects.create("Test", "test")
    assert res["id"] == "p1"

@responses.activate
def test_projects_history():
    client = HomelabClient(developer_token="dev123")
    responses.add(
        responses.GET,
        "https://localhost:8443/api/v1/baas/projects/p1/history?limit=10",
        json={"operations": []},
        status=200
    )
    res = client.projects.history("p1", limit=10)
    assert "operations" in res

@responses.activate
def test_projects_status():
    client = HomelabClient(developer_token="dev123")
    responses.add(
        responses.GET,
        "https://localhost:8443/api/v1/baas/projects/p1/status",
        json={"state": "running"},
        status=200
    )
    res = client.projects.status("p1")
    assert res["state"] == "running"

@responses.activate
def test_schema_create():
    client = HomelabClient(developer_token="dev123")
    responses.add(
        responses.POST,
        "https://localhost:8443/api/v1/baas/projects/p1/tables",
        json={"name": "users"},
        status=201
    )
    res = client.schema.create("p1", "users", [{"name": "id", "type": "text"}])
    assert res["name"] == "users"

@responses.activate
def test_apikeys_create():
    client = HomelabClient(developer_token="dev123")
    responses.add(
        responses.POST,
        "https://localhost:8443/api/v1/baas/projects/p1/keys",
        json={"key": "pk_live_123"},
        status=201
    )
    res = client.apikeys.create("p1", "production")
    assert res["key"] == "pk_live_123"

@responses.activate
def test_teammates_add():
    client = HomelabClient(developer_token="dev123")
    responses.add(
        responses.POST,
        "https://localhost:8443/api/v1/baas/projects/p1/members",
        json={"email": "team@test.com", "role": "viewer"},
        status=201
    )
    res = client.teammates.add("p1", "team@test.com", "viewer")
    assert res["role"] == "viewer"
