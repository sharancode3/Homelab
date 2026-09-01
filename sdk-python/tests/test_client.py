import pytest
import responses
from homelab_sdk import HomelabClient
from homelab_sdk.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    ServerError
)

@responses.activate
def test_client_dev_token_success():
    client = HomelabClient(developer_token="test_dev_token")
    responses.add(
        responses.GET,
        "https://localhost:8443/projects/",
        json=[{"name": "proj1"}],
        status=200
    )

    result = client.request("GET", "/projects/", require_dev_token=True)
    assert len(result) == 1
    assert result[0]["name"] == "proj1"

    # Verify the header was set correctly
    req = responses.calls[0].request
    assert req.headers["Authorization"] == "Bearer test_dev_token"
    assert "X-Project-API-Key" not in req.headers

def test_client_dev_token_missing():
    client = HomelabClient(api_key="pk_live_123")
    with pytest.raises(ValueError, match="developer_token is required"):
        client.request("GET", "/projects/", require_dev_token=True)

@responses.activate
def test_client_api_key_success():
    client = HomelabClient(api_key="pk_live_123")
    responses.add(
        responses.GET,
        "https://localhost:8443/projects/p1/data/t1",
        json=[{"data": {"id": 1}}],
        status=200
    )

    result = client.request("GET", "/projects/p1/data/t1", require_api_key=True)
    assert result[0]["data"]["id"] == 1

    req = responses.calls[0].request
    assert req.headers["X-Project-API-Key"] == "pk_live_123"
    assert "Authorization" not in req.headers

def test_client_api_key_missing():
    client = HomelabClient(developer_token="dev_token")
    with pytest.raises(ValueError, match="api_key is required"):
        client.request("GET", "/data", require_api_key=True)

@responses.activate
def test_client_end_user_token_success():
    client = HomelabClient(end_user_token="user_token_123")
    responses.add(
        responses.GET,
        "https://localhost:8443/p1/auth/me",
        json={"email": "user@example.com"},
        status=200
    )

    result = client.request("GET", "/p1/auth/me", require_end_user_token=True)
    assert result["email"] == "user@example.com"

    req = responses.calls[0].request
    assert req.headers["Authorization"] == "Bearer user_token_123"

def test_client_end_user_token_missing():
    client = HomelabClient(developer_token="dev_token")
    with pytest.raises(ValueError, match="end_user_token is required"):
        client.request("GET", "/me", require_end_user_token=True)

@responses.activate
def test_http_error_mapping_401():
    client = HomelabClient(developer_token="test")
    responses.add(
        responses.GET,
        "https://localhost:8443/projects/",
        json={"detail": "Invalid token"},
        status=401
    )

    with pytest.raises(AuthenticationError) as exc:
        client.request("GET", "/projects/", require_dev_token=True)
    assert exc.value.status_code == 401

@responses.activate
def test_http_error_mapping_403():
    client = HomelabClient(developer_token="test")
    responses.add(
        responses.GET,
        "https://localhost:8443/projects/",
        json={"detail": "Forbidden"},
        status=403
    )

    with pytest.raises(AuthorizationError):
        client.request("GET", "/projects/", require_dev_token=True)

@responses.activate
def test_http_error_mapping_404():
    client = HomelabClient(developer_token="test")
    responses.add(
        responses.GET,
        "https://localhost:8443/projects/123",
        json={"detail": "Not found"},
        status=404
    )

    with pytest.raises(NotFoundError):
        client.request("GET", "/projects/123", require_dev_token=True)

@responses.activate
def test_http_error_mapping_422():
    client = HomelabClient(developer_token="test")
    responses.add(
        responses.POST,
        "https://localhost:8443/projects/",
        json={"detail": [{"msg": "Field required"}]},
        status=422
    )

    with pytest.raises(ValidationError):
        client.request("POST", "/projects/", require_dev_token=True)

@responses.activate
def test_http_error_mapping_500():
    client = HomelabClient(developer_token="test")
    responses.add(
        responses.GET,
        "https://localhost:8443/projects/",
        json={"detail": "Internal error"},
        status=500
    )

    with pytest.raises(ServerError):
        client.request("GET", "/projects/", require_dev_token=True)
