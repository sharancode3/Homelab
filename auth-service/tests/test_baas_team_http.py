"""
Phase 11 Step 6 — Team Collaboration: HTTP-Layer RBAC Integration Tests

Tests use FastAPI TestClient to verify that every route's Depends() guard
enforces roles correctly end-to-end (not just at the service layer).

Locked decisions:
  Q1: Admin CAN manage members (not just Owner)
  Q2: API Key is the exclusive Data Plane credential
  Q3: description field not added
"""
import uuid
import unittest
from fastapi.testclient import TestClient
from app.main import app


def _uid() -> str:
    return uuid.uuid4().hex[:8]


class TeamHttpBase(unittest.TestCase):
    """
    Base class that sets up a 4-role project via the HTTP API.

    Topology (shared per test class via setUpClass):
        project owned by owner_user
        admin_user  -> admin
        dev_user    -> developer
        viewer_user -> viewer
        outsider    -> not a member
    """

    client: TestClient
    project_id: str
    owner_token: str
    admin_token: str
    dev_token: str
    viewer_token: str
    outsider_token: str
    owner_user_id: str
    admin_user_id: str
    dev_user_id: str
    viewer_user_id: str
    outsider_user_id: str

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls._setup_team()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    @classmethod
    def _register_and_login(cls, username: str, email: str, password: str = "password123") -> tuple:
        cls.client.post("/api/v1/auth/register", json={
            "username": username, "email": email, "password": password
        })
        res = cls.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        token = res.json()["access_token"]
        me = cls.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        return token, me["user_id"]

    @classmethod
    def _setup_team(cls):
        tag = _uid()
        cls.owner_token, cls.owner_user_id = cls._register_and_login(
            f"owner_{tag}", f"owner_{tag}@t.com")
        cls.admin_token, cls.admin_user_id = cls._register_and_login(
            f"admin_{tag}", f"admin_{tag}@t.com")
        cls.dev_token, cls.dev_user_id = cls._register_and_login(
            f"dev_{tag}", f"dev_{tag}@t.com")
        cls.viewer_token, cls.viewer_user_id = cls._register_and_login(
            f"viewer_{tag}", f"viewer_{tag}@t.com")
        cls.outsider_token, cls.outsider_user_id = cls._register_and_login(
            f"outsider_{tag}", f"outsider_{tag}@t.com")

        owner_h = {"Authorization": f"Bearer {cls.owner_token}"}
        res = cls.client.post("/api/v1/baas/projects/", json={
            "project_name": "Team Test Project",
            "project_slug": f"team-test-{tag}",
        }, headers=owner_h)
        assert res.status_code == 201, f"Project creation failed: {res.text}"
        cls.project_id = res.json()["project_id"]

        cls.client.post(
            f"/api/v1/baas/projects/{cls.project_id}/members",
            json={"email": f"admin_{tag}@t.com", "role": "admin"},
            headers=owner_h)
        cls.client.post(
            f"/api/v1/baas/projects/{cls.project_id}/members",
            json={"email": f"dev_{tag}@t.com", "role": "developer"},
            headers=owner_h)
        cls.client.post(
            f"/api/v1/baas/projects/{cls.project_id}/members",
            json={"email": f"viewer_{tag}@t.com", "role": "viewer"},
            headers=owner_h)

    def _h(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _url(self, path: str = "") -> str:
        return f"/api/v1/baas/projects/{self.project_id}{path}"


# ──────────────────────────────────────────────────────────────────────────────
# Read Operations — all 4 roles can read
# ──────────────────────────────────────────────────────────────────────────────

class TestReadOperationsAllRoles(TeamHttpBase):

    def test_owner_can_read_members(self):
        res = self.client.get(self._url("/members"), headers=self._h(self.owner_token))
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_admin_can_read_members(self):
        res = self.client.get(self._url("/members"), headers=self._h(self.admin_token))
        self.assertEqual(res.status_code, 200)

    def test_developer_can_read_members(self):
        res = self.client.get(self._url("/members"), headers=self._h(self.dev_token))
        self.assertEqual(res.status_code, 200)

    def test_viewer_can_read_members(self):
        res = self.client.get(self._url("/members"), headers=self._h(self.viewer_token))
        self.assertEqual(res.status_code, 200)

    def test_non_member_cannot_read_members(self):
        res = self.client.get(self._url("/members"), headers=self._h(self.outsider_token))
        self.assertIn(res.status_code, (401, 403))

    def test_unauthenticated_cannot_read_members(self):
        res = self.client.get(self._url("/members"))
        self.assertEqual(res.status_code, 401)

    def test_owner_can_read_project(self):
        res = self.client.get(self._url(), headers=self._h(self.owner_token))
        self.assertEqual(res.status_code, 200)

    def test_developer_can_read_project(self):
        res = self.client.get(self._url(), headers=self._h(self.dev_token))
        self.assertEqual(res.status_code, 200)

    def test_viewer_can_read_project(self):
        res = self.client.get(self._url(), headers=self._h(self.viewer_token))
        self.assertEqual(res.status_code, 200)

    def test_non_member_cannot_read_project(self):
        res = self.client.get(self._url(), headers=self._h(self.outsider_token))
        self.assertIn(res.status_code, (401, 403))

    def test_all_roles_can_list_tables(self):
        for token in [self.owner_token, self.admin_token, self.dev_token, self.viewer_token]:
            res = self.client.get(self._url("/tables"), headers=self._h(token))
            self.assertEqual(res.status_code, 200)

    def test_non_member_cannot_list_tables(self):
        res = self.client.get(self._url("/tables"), headers=self._h(self.outsider_token))
        self.assertIn(res.status_code, (401, 403))


# ──────────────────────────────────────────────────────────────────────────────
# Add Member — Owner and Admin only
# ──────────────────────────────────────────────────────────────────────────────

class TestAddMemberRBAC(TeamHttpBase):

    @classmethod
    def _new_email(cls, prefix: str) -> str:
        tag = _uid()
        email = f"{prefix}_{tag}@t.com"
        cls.client.post("/api/v1/auth/register", json={
            "username": f"{prefix}_{tag}", "email": email, "password": "p"
        })
        return email

    def test_owner_can_add_member(self):
        email = self._new_email("nm_o")
        res = self.client.post(self._url("/members"),
            json={"email": email, "role": "developer"}, headers=self._h(self.owner_token))
        self.assertIn(res.status_code, (200, 201))

    def test_admin_can_add_member(self):
        email = self._new_email("nm_a")
        res = self.client.post(self._url("/members"),
            json={"email": email, "role": "viewer"}, headers=self._h(self.admin_token))
        self.assertIn(res.status_code, (200, 201))

    def test_developer_cannot_add_member(self):
        email = self._new_email("nm_d")
        res = self.client.post(self._url("/members"),
            json={"email": email, "role": "viewer"}, headers=self._h(self.dev_token))
        self.assertIn(res.status_code, (401, 403))

    def test_viewer_cannot_add_member(self):
        email = self._new_email("nm_v")
        res = self.client.post(self._url("/members"),
            json={"email": email, "role": "viewer"}, headers=self._h(self.viewer_token))
        self.assertIn(res.status_code, (401, 403))

    def test_non_member_cannot_add_member(self):
        email = self._new_email("nm_nm")
        res = self.client.post(self._url("/members"),
            json={"email": email, "role": "developer"}, headers=self._h(self.outsider_token))
        self.assertIn(res.status_code, (401, 403))

    def test_unauthenticated_cannot_add_member(self):
        email = self._new_email("nm_ua")
        res = self.client.post(self._url("/members"), json={"email": email, "role": "developer"})
        self.assertEqual(res.status_code, 401)

    def test_admin_cannot_add_owner(self):
        email = self._new_email("nm_ao")
        res = self.client.post(self._url("/members"),
            json={"email": email, "role": "owner"}, headers=self._h(self.admin_token))
        self.assertIn(res.status_code, (400, 403))


# ──────────────────────────────────────────────────────────────────────────────
# Update Member Role — Owner and Admin only
# ──────────────────────────────────────────────────────────────────────────────

class TestUpdateMemberRoleRBAC(TeamHttpBase):

    def test_owner_can_update_developer_role(self):
        res = self.client.put(self._url(f"/members/{self.dev_user_id}"),
            json={"role": "viewer"}, headers=self._h(self.owner_token))
        self.assertEqual(res.status_code, 200)
        # Restore
        self.client.put(self._url(f"/members/{self.dev_user_id}"),
            json={"role": "developer"}, headers=self._h(self.owner_token))

    def test_admin_can_update_viewer_role(self):
        res = self.client.put(self._url(f"/members/{self.viewer_user_id}"),
            json={"role": "developer"}, headers=self._h(self.admin_token))
        self.assertEqual(res.status_code, 200)
        # Restore
        self.client.put(self._url(f"/members/{self.viewer_user_id}"),
            json={"role": "viewer"}, headers=self._h(self.admin_token))

    def test_admin_cannot_modify_owner_role(self):
        res = self.client.put(self._url(f"/members/{self.owner_user_id}"),
            json={"role": "developer"}, headers=self._h(self.admin_token))
        self.assertIn(res.status_code, (400, 403))

    def test_admin_cannot_promote_to_owner(self):
        res = self.client.put(self._url(f"/members/{self.dev_user_id}"),
            json={"role": "owner"}, headers=self._h(self.admin_token))
        self.assertIn(res.status_code, (400, 403))

    def test_developer_cannot_update_member_role(self):
        res = self.client.put(self._url(f"/members/{self.viewer_user_id}"),
            json={"role": "developer"}, headers=self._h(self.dev_token))
        self.assertIn(res.status_code, (401, 403))

    def test_viewer_cannot_update_member_role(self):
        res = self.client.put(self._url(f"/members/{self.dev_user_id}"),
            json={"role": "admin"}, headers=self._h(self.viewer_token))
        self.assertIn(res.status_code, (401, 403))

    def test_unauthenticated_cannot_update_member_role(self):
        res = self.client.put(self._url(f"/members/{self.dev_user_id}"), json={"role": "admin"})
        self.assertEqual(res.status_code, 401)

    def test_owner_cannot_demote_last_owner(self):
        res = self.client.put(self._url(f"/members/{self.owner_user_id}"),
            json={"role": "admin"}, headers=self._h(self.owner_token))
        self.assertIn(res.status_code, (400, 403))


# ──────────────────────────────────────────────────────────────────────────────
# Remove Member — Owner and Admin only
# ──────────────────────────────────────────────────────────────────────────────

class TestRemoveMemberRBAC(TeamHttpBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Add a dedicated removable member for this class
        tag = _uid()
        cls._removable_email = f"removable_{tag}@t.com"
        cls.client.post("/api/v1/auth/register", json={
            "username": f"removable_{tag}",
            "email": cls._removable_email,
            "password": "p"
        })
        res = cls.client.post("/api/v1/auth/login", json={
            "email": cls._removable_email, "password": "p"
        })
        cls._removable_token = res.json()["access_token"]
        me = cls.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {cls._removable_token}"}
        ).json()
        cls._removable_user_id = me["user_id"]
        # Add them to the project
        cls.client.post(
            f"/api/v1/baas/projects/{cls.project_id}/members",
            json={"email": cls._removable_email, "role": "developer"},
            headers={"Authorization": f"Bearer {cls.owner_token}"}
        )

    def _re_add(self):
        self.client.post(self._url("/members"),
            json={"email": self._removable_email, "role": "developer"},
            headers=self._h(self.owner_token))

    def test_developer_cannot_remove_member(self):
        res = self.client.delete(self._url(f"/members/{self._removable_user_id}"),
            headers=self._h(self.dev_token))
        self.assertIn(res.status_code, (401, 403))

    def test_viewer_cannot_remove_member(self):
        res = self.client.delete(self._url(f"/members/{self._removable_user_id}"),
            headers=self._h(self.viewer_token))
        self.assertIn(res.status_code, (401, 403))

    def test_admin_cannot_remove_owner(self):
        res = self.client.delete(self._url(f"/members/{self.owner_user_id}"),
            headers=self._h(self.admin_token))
        self.assertIn(res.status_code, (400, 403))

    def test_owner_cannot_remove_last_owner(self):
        res = self.client.delete(self._url(f"/members/{self.owner_user_id}"),
            headers=self._h(self.owner_token))
        self.assertIn(res.status_code, (400, 403))

    def test_unauthenticated_cannot_remove_member(self):
        res = self.client.delete(self._url(f"/members/{self._removable_user_id}"))
        self.assertEqual(res.status_code, 401)

    def test_admin_can_remove_developer(self):
        res = self.client.delete(self._url(f"/members/{self._removable_user_id}"),
            headers=self._h(self.admin_token))
        self.assertIn(res.status_code, (200, 204))
        self._re_add()

    def test_removed_member_loses_project_access(self):
        # Remove the member
        self.client.delete(self._url(f"/members/{self._removable_user_id}"),
            headers=self._h(self.owner_token))
        # That user should now be blocked from all project routes
        res = self.client.get(self._url("/members"), headers=self._h(self._removable_token))
        self.assertIn(res.status_code, (401, 403))
        res2 = self.client.get(self._url(), headers=self._h(self._removable_token))
        self.assertIn(res2.status_code, (401, 403))
        # Restore
        self._re_add()


# ──────────────────────────────────────────────────────────────────────────────
# Table Schema Management — Owner and Admin only
# ──────────────────────────────────────────────────────────────────────────────

class TestTableSchemaRBAC(TeamHttpBase):

    def test_owner_can_create_table(self):
        res = self.client.post(self._url("/tables"),
            json={"name": f"tbl_o_{_uid()}", "columns": {"v": "TEXT"}},
            headers=self._h(self.owner_token))
        self.assertIn(res.status_code, (200, 201))

    def test_admin_can_create_table(self):
        res = self.client.post(self._url("/tables"),
            json={"name": f"tbl_a_{_uid()}", "columns": {"v": "TEXT"}},
            headers=self._h(self.admin_token))
        self.assertIn(res.status_code, (200, 201))

    def test_developer_cannot_create_table(self):
        res = self.client.post(self._url("/tables"),
            json={"name": f"tbl_d_{_uid()}", "columns": {"v": "TEXT"}},
            headers=self._h(self.dev_token))
        self.assertIn(res.status_code, (401, 403))

    def test_viewer_cannot_create_table(self):
        res = self.client.post(self._url("/tables"),
            json={"name": f"tbl_v_{_uid()}", "columns": {"v": "TEXT"}},
            headers=self._h(self.viewer_token))
        self.assertIn(res.status_code, (401, 403))

    def test_non_member_cannot_create_table(self):
        res = self.client.post(self._url("/tables"),
            json={"name": f"tbl_nm_{_uid()}", "columns": {"v": "TEXT"}},
            headers=self._h(self.outsider_token))
        self.assertIn(res.status_code, (401, 403))

    def test_unauthenticated_cannot_create_table(self):
        res = self.client.post(self._url("/tables"),
            json={"name": f"tbl_ua_{_uid()}", "columns": {"v": "TEXT"}})
        self.assertEqual(res.status_code, 401)

    def test_developer_cannot_delete_table(self):
        name = f"tbl_del_d_{_uid()}"
        self.client.post(self._url("/tables"),
            json={"name": name, "columns": {"v": "TEXT"}}, headers=self._h(self.owner_token))
        res = self.client.delete(self._url(f"/tables/{name}"), headers=self._h(self.dev_token))
        self.assertIn(res.status_code, (401, 403))

    def test_viewer_cannot_delete_table(self):
        name = f"tbl_del_v_{_uid()}"
        self.client.post(self._url("/tables"),
            json={"name": name, "columns": {"v": "TEXT"}}, headers=self._h(self.owner_token))
        res = self.client.delete(self._url(f"/tables/{name}"), headers=self._h(self.viewer_token))
        self.assertIn(res.status_code, (401, 403))

    def test_admin_can_delete_table(self):
        name = f"tbl_del_a_{_uid()}"
        self.client.post(self._url("/tables"),
            json={"name": name, "columns": {"v": "TEXT"}}, headers=self._h(self.owner_token))
        res = self.client.delete(self._url(f"/tables/{name}"), headers=self._h(self.admin_token))
        self.assertIn(res.status_code, (200, 204))


# ──────────────────────────────────────────────────────────────────────────────
# API Key Management — Owner and Admin only
# ──────────────────────────────────────────────────────────────────────────────

class TestApiKeyManagementRBAC(TeamHttpBase):

    def test_owner_can_create_api_key(self):
        res = self.client.post(self._url("/keys"),
            json={"name": "owner-key"}, headers=self._h(self.owner_token))
        self.assertEqual(res.status_code, 200)

    def test_admin_can_create_api_key(self):
        res = self.client.post(self._url("/keys"),
            json={"name": "admin-key"}, headers=self._h(self.admin_token))
        self.assertEqual(res.status_code, 200)

    def test_developer_cannot_create_api_key(self):
        res = self.client.post(self._url("/keys"),
            json={"name": "dev-key"}, headers=self._h(self.dev_token))
        self.assertIn(res.status_code, (401, 403))

    def test_viewer_cannot_create_api_key(self):
        res = self.client.post(self._url("/keys"),
            json={"name": "viewer-key"}, headers=self._h(self.viewer_token))
        self.assertIn(res.status_code, (401, 403))

    def test_developer_cannot_list_api_keys(self):
        res = self.client.get(self._url("/keys"), headers=self._h(self.dev_token))
        self.assertIn(res.status_code, (401, 403))

    def test_viewer_cannot_list_api_keys(self):
        res = self.client.get(self._url("/keys"), headers=self._h(self.viewer_token))
        self.assertIn(res.status_code, (401, 403))

    def test_developer_cannot_revoke_api_key(self):
        key_res = self.client.post(self._url("/keys"),
            json={"name": "to-revoke"}, headers=self._h(self.owner_token))
        key_id = key_res.json()["key_id"]
        res = self.client.delete(self._url(f"/keys/{key_id}"), headers=self._h(self.dev_token))
        self.assertIn(res.status_code, (401, 403))

    def test_unauthenticated_cannot_create_api_key(self):
        res = self.client.post(self._url("/keys"), json={"name": "unauth"})
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
