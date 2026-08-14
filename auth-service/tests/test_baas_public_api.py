"""
Phase 12 — Public BaaS API: HTTP Integration Tests

Verifies the public API contract changes made in Phase 12:
  - Gap 1: POST /auth/refresh issues a new access token
  - Gap 2: POST resource routes return HTTP 201
  - Gap 3: CORS headers present on responses
  - Gap 4: Platform ops (deploy/backup/validate) enforce correct RBAC
  - Gap 5: GET /health returns 200 with no auth
"""
import unittest
import uuid
from fastapi.testclient import TestClient
from app.main import app


def _uid() -> str:
    return uuid.uuid4().hex[:8]


class PublicAPIBase(unittest.TestCase):
    """Shared TestClient + convenience helpers."""

    client: TestClient

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    @classmethod
    def _register_and_login(cls, username: str, email: str, password: str = "password123") -> tuple:
        cls.client.post("/api/v1/auth/register", json={
            "username": username, "email": email, "password": password
        })
        res = cls.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        body = res.json()
        return body["access_token"], body["refresh_token"]

    def _h(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Gap 5 — Platform health endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestPlatformHealth(PublicAPIBase):

    def test_health_returns_200(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)

    def test_health_body(self):
        res = self.client.get("/health")
        body = res.json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("version", body)

    def test_health_requires_no_auth(self):
        # No Authorization header — must still return 200
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)


# ─────────────────────────────────────────────────────────────────────────────
# Gap 3 — CORS headers
# ─────────────────────────────────────────────────────────────────────────────

class TestCORSHeaders(PublicAPIBase):

    def test_cors_header_on_health(self):
        res = self.client.get("/health", headers={"Origin": "http://localhost:3000"})
        # With allow_origins=["*"] the header should be present
        self.assertIn("access-control-allow-origin", res.headers)

    def test_cors_preflight_on_auth_login(self):
        res = self.client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        self.assertIn(res.status_code, (200, 204))
        self.assertIn("access-control-allow-origin", res.headers)


# ─────────────────────────────────────────────────────────────────────────────
# Gap 1 — POST /auth/refresh
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthRefresh(PublicAPIBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tag = _uid()
        cls.access_token, cls.refresh_token = cls._register_and_login(
            f"refresh_u_{tag}", f"refresh_{tag}@t.com"
        )

    def test_valid_refresh_returns_new_access_token(self):
        res = self.client.post("/api/v1/auth/refresh",
            json={"refresh_token": self.refresh_token})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("access_token", body)
        self.assertEqual(body["token_type"], "bearer")

    def test_new_access_token_is_usable(self):
        res = self.client.post("/api/v1/auth/refresh",
            json={"refresh_token": self.refresh_token})
        new_token = res.json()["access_token"]
        me_res = self.client.get("/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_token}"})
        self.assertEqual(me_res.status_code, 200)

    def test_access_token_rejected_as_refresh(self):
        # Sending the access token where a refresh token is expected → 401
        res = self.client.post("/api/v1/auth/refresh",
            json={"refresh_token": self.access_token})
        self.assertEqual(res.status_code, 401)

    def test_garbage_token_rejected(self):
        res = self.client.post("/api/v1/auth/refresh",
            json={"refresh_token": "not.a.real.token"})
        self.assertEqual(res.status_code, 401)

    def test_empty_token_rejected(self):
        res = self.client.post("/api/v1/auth/refresh",
            json={"refresh_token": ""})
        self.assertIn(res.status_code, (401, 422))

    def test_missing_refresh_token_field_rejected(self):
        res = self.client.post("/api/v1/auth/refresh", json={})
        self.assertEqual(res.status_code, 422)

    def test_refresh_does_not_issue_new_refresh_token(self):
        # Response must only contain access_token, not a new refresh_token
        res = self.client.post("/api/v1/auth/refresh",
            json={"refresh_token": self.refresh_token})
        body = res.json()
        self.assertNotIn("refresh_token", body)


# ─────────────────────────────────────────────────────────────────────────────
# Gap 2 — HTTP 201 on resource-creating POST routes
# ─────────────────────────────────────────────────────────────────────────────

class TestHTTP201StatusCodes(PublicAPIBase):
    """Verify all resource-creating POST routes return 201, not 200."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tag = _uid()
        cls.access_token, _ = cls._register_and_login(
            f"status_u_{tag}", f"status_{tag}@t.com"
        )
        owner_h = {"Authorization": f"Bearer {cls.access_token}"}
        res = cls.client.post("/api/v1/baas/projects/", json={
            "project_name": "Status Test Project",
            "project_slug": f"status-{tag}",
        }, headers=owner_h)
        assert res.status_code == 201, f"Project create failed: {res.text}"
        cls.project_id = res.json()["project_id"]

        # Create an API key for data-plane tests
        key_res = cls.client.post(
            f"/api/v1/baas/projects/{cls.project_id}/keys",
            json={"name": "test-key"},
            headers=owner_h,
        )
        cls.api_key = key_res.json()["key"]
        cls.owner_h = owner_h

    def test_create_project_returns_201(self):
        tag = _uid()
        res = self.client.post("/api/v1/baas/projects/", json={
            "project_name": "201 Check",
            "project_slug": f"check-{tag}",
        }, headers=self.owner_h)
        self.assertEqual(res.status_code, 201)

    def test_create_table_returns_201(self):
        name = f"tbl_{_uid()}"
        res = self.client.post(
            f"/api/v1/baas/projects/{self.project_id}/tables",
            json={"name": name, "columns": {"val": "TEXT"}},
            headers=self.owner_h,
        )
        self.assertEqual(res.status_code, 201)

    def test_create_api_key_returns_201(self):
        res = self.client.post(
            f"/api/v1/baas/projects/{self.project_id}/keys",
            json={"name": f"key-{_uid()}"},
            headers=self.owner_h,
        )
        self.assertEqual(res.status_code, 201)

    def test_add_member_returns_201(self):
        tag = _uid()
        email = f"newmember_{tag}@t.com"
        self.client.post("/api/v1/auth/register", json={
            "username": f"nm_{tag}", "email": email, "password": "p"
        })
        res = self.client.post(
            f"/api/v1/baas/projects/{self.project_id}/members",
            json={"email": email, "role": "developer"},
            headers=self.owner_h,
        )
        self.assertEqual(res.status_code, 201)

    def test_insert_row_returns_201(self):
        # Create a table first
        tbl = f"rows_{_uid()}"
        self.client.post(
            f"/api/v1/baas/projects/{self.project_id}/tables",
            json={"name": tbl, "columns": {"v": "TEXT"}},
            headers=self.owner_h,
        )
        res = self.client.post(
            f"/api/v1/baas/projects/{self.project_id}/data/{tbl}",
            json={"v": "hello"},
            headers={
                "X-Project-API-Key": self.api_key,
                "X-Project-ID": self.project_id,
            },
        )
        self.assertEqual(res.status_code, 201)

    def test_register_still_returns_201(self):
        tag = _uid()
        res = self.client.post("/api/v1/auth/register", json={
            "username": f"reg_{tag}", "email": f"reg_{tag}@t.com", "password": "password123"
        })
        self.assertEqual(res.status_code, 201)


# ─────────────────────────────────────────────────────────────────────────────
# Gap 4 — Platform op RBAC (validate/deploy/backup/restore)
# ─────────────────────────────────────────────────────────────────────────────

class TestPlatformOpsRBAC(PublicAPIBase):
    """
    Operations on /baas/projects/{id}/validate, deploy, backup, restore
    must enforce the established RBAC:
        validate: require_developer (owner, admin, developer)
        deploy:   require_developer (owner, admin, developer)
        backup:   require_admin    (owner, admin)
        restore:  require_admin    (owner, admin)

    API keys must never be accepted for these Control Plane operations.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tag = _uid()
        cls.owner_token, _ = cls._register_and_login(f"pop_owner_{tag}", f"pop_owner_{tag}@t.com")
        cls.dev_token, _ = cls._register_and_login(f"pop_dev_{tag}", f"pop_dev_{tag}@t.com")
        cls.viewer_token, _ = cls._register_and_login(f"pop_viewer_{tag}", f"pop_viewer_{tag}@t.com")
        cls.outsider_token, _ = cls._register_and_login(f"pop_out_{tag}", f"pop_out_{tag}@t.com")

        owner_h = {"Authorization": f"Bearer {cls.owner_token}"}
        res = cls.client.post("/api/v1/baas/projects/", json={
            "project_name": "OpsRBAC Project",
            "project_slug": f"ops-rbac-{tag}",
        }, headers=owner_h)
        assert res.status_code == 201
        cls.project_id = res.json()["project_id"]

        # Fetch email for developer
        dev_me = cls.client.get("/api/v1/auth/me",
            headers={"Authorization": f"Bearer {cls.dev_token}"}).json()
        viewer_me = cls.client.get("/api/v1/auth/me",
            headers={"Authorization": f"Bearer {cls.viewer_token}"}).json()

        cls.client.post(f"/api/v1/baas/projects/{cls.project_id}/members",
            json={"email": f"pop_dev_{tag}@t.com", "role": "developer"}, headers=owner_h)
        cls.client.post(f"/api/v1/baas/projects/{cls.project_id}/members",
            json={"email": f"pop_viewer_{tag}@t.com", "role": "viewer"}, headers=owner_h)

        key_res = cls.client.post(f"/api/v1/baas/projects/{cls.project_id}/keys",
            json={"name": "ops-key"}, headers=owner_h)
        cls.api_key = key_res.json()["key"]

    def _op_url(self, op: str) -> str:
        return f"/api/v1/baas/projects/{self.project_id}/{op}"

    # validate: developer and above allowed
    def test_owner_can_validate(self):
        res = self.client.post(self._op_url("validate"),
            headers=self._h(self.owner_token))
        self.assertNotIn(res.status_code, (401, 403))

    def test_developer_can_validate(self):
        res = self.client.post(self._op_url("validate"),
            headers=self._h(self.dev_token))
        self.assertNotIn(res.status_code, (401, 403))

    def test_viewer_cannot_validate(self):
        res = self.client.post(self._op_url("validate"),
            headers=self._h(self.viewer_token))
        self.assertIn(res.status_code, (401, 403))

    def test_non_member_cannot_validate(self):
        res = self.client.post(self._op_url("validate"),
            headers=self._h(self.outsider_token))
        self.assertIn(res.status_code, (401, 403))

    def test_unauthenticated_cannot_validate(self):
        res = self.client.post(self._op_url("validate"))
        self.assertEqual(res.status_code, 401)

    # backup: admin and above only
    def test_owner_can_backup(self):
        res = self.client.post(self._op_url("backup"),
            json={"requested_by": "test"}, headers=self._h(self.owner_token))
        self.assertNotIn(res.status_code, (401, 403))

    def test_developer_cannot_backup(self):
        res = self.client.post(self._op_url("backup"),
            json={"requested_by": "test"}, headers=self._h(self.dev_token))
        self.assertIn(res.status_code, (401, 403))

    def test_viewer_cannot_backup(self):
        res = self.client.post(self._op_url("backup"),
            json={"requested_by": "test"}, headers=self._h(self.viewer_token))
        self.assertIn(res.status_code, (401, 403))

    # API key must never be accepted for Control Plane operations
    def test_api_key_cannot_validate(self):
        res = self.client.post(self._op_url("validate"), headers={
            "X-Project-API-Key": self.api_key,
            "X-Project-ID": self.project_id,
        })
        self.assertEqual(res.status_code, 401)

    def test_api_key_cannot_backup(self):
        res = self.client.post(self._op_url("backup"),
            json={"requested_by": "test"}, headers={
                "X-Project-API-Key": self.api_key,
                "X-Project-ID": self.project_id,
            })
        self.assertEqual(res.status_code, 401)

    def test_unauthenticated_cannot_backup(self):
        res = self.client.post(self._op_url("backup"),
            json={"requested_by": "test"})
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
