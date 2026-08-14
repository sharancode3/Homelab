import unittest
from fastapi import HTTPException
from app.api.baas_service import BaaSProjectServiceLayer
from app.api.service import APIServiceLayer
from app.project_registry_manager import ProjectRegistryManager
from app.storage.providers.sqlite import SQLiteProjectAuthorizationRepository
from app.identity.models import DeveloperUser
from unittest.mock import MagicMock
from app.api.dependencies import verify_project_api_key

class MockUserRepository:
    def __init__(self):
        from datetime import datetime, UTC
        self.users = {
            "u1": DeveloperUser(user_id="u1", username="owner", email="owner@x.com", hashed_password="", created_at=datetime.now(UTC)),
            "u2": DeveloperUser(user_id="u2", username="admin", email="admin@x.com", hashed_password="", created_at=datetime.now(UTC)),
            "u3": DeveloperUser(user_id="u3", username="dev", email="dev@x.com", hashed_password="", created_at=datetime.now(UTC)),
            "u4": DeveloperUser(user_id="u4", username="viewer", email="viewer@x.com", hashed_password="", created_at=datetime.now(UTC)),
        }
        self.by_email = {u.email: u for u in self.users.values()}

    def get_by_user_id(self, user_id):
        return self.users.get(user_id)

    def get_by_email(self, email):
        return self.by_email.get(email)

class TestBaaSAPIKeys(unittest.TestCase):
    def setUp(self):
        self.authz_repo = SQLiteProjectAuthorizationRepository(db_path=":memory:")
        self.registry = MagicMock(spec=ProjectRegistryManager)
        self.internal_service = MagicMock(spec=APIServiceLayer)
        self.user_repo = MockUserRepository()
        self.service = BaaSProjectServiceLayer(
            self.internal_service, self.authz_repo, self.registry, self.user_repo
        )

        self.project_id = "proj_11112222"
        self.authz_repo.add_member(self.project_id, "u1", "owner")

    def test_create_and_list_api_key(self):
        key_res = self.service.create_api_key(self.project_id, "Test Key", "u1")
        self.assertTrue(key_res["key"].startswith("pk_live_"))

        keys = self.service.list_api_keys(self.project_id)
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["name"], "Test Key")
        self.assertTrue(keys[0]["is_active"])

    def test_revoke_api_key(self):
        key_res = self.service.create_api_key(self.project_id, "Test Key", "u1")
        key_id = key_res["key_id"]

        self.service.revoke_api_key(self.project_id, key_id)
        keys = self.service.list_api_keys(self.project_id)
        self.assertFalse(keys[0]["is_active"])

    def test_rotate_api_key(self):
        key_res = self.service.create_api_key(self.project_id, "Test Key", "u1")
        old_key_id = key_res["key_id"]

        new_key_res = self.service.rotate_api_key(self.project_id, old_key_id, "u1")
        self.assertNotEqual(old_key_id, new_key_res["key_id"])

        keys = self.service.list_api_keys(self.project_id)
        self.assertEqual(len(keys), 2)
        old_key = next(k for k in keys if k["key_id"] == old_key_id)
        new_key = next(k for k in keys if k["key_id"] == new_key_res["key_id"])
        self.assertFalse(old_key["is_active"])
        self.assertTrue(new_key["is_active"])

    def test_verify_project_api_key(self):
        key_res = self.service.create_api_key(self.project_id, "Test Key", "u1")
        full_key = key_res["key"]

        verified_project_id = verify_project_api_key(self.project_id, full_key, self.authz_repo)
        self.assertEqual(verified_project_id, self.project_id)

    def test_verify_project_api_key_invalid_format(self):
        with self.assertRaises(HTTPException) as cm:
            verify_project_api_key(self.project_id, "invalid_key", self.authz_repo)
        self.assertEqual(cm.exception.status_code, 401)

    def test_verify_project_api_key_wrong_project(self):
        key_res = self.service.create_api_key(self.project_id, "Test Key", "u1")
        full_key = key_res["key"]

        with self.assertRaises(HTTPException) as cm:
            verify_project_api_key("proj_wrong", full_key, self.authz_repo)
        self.assertEqual(cm.exception.status_code, 403)

    def test_verify_project_api_key_revoked(self):
        key_res = self.service.create_api_key(self.project_id, "Test Key", "u1")
        self.service.revoke_api_key(self.project_id, key_res["key_id"])

        with self.assertRaises(HTTPException) as cm:
            verify_project_api_key(self.project_id, key_res["key"], self.authz_repo)
        self.assertEqual(cm.exception.status_code, 401)

if __name__ == "__main__":
    unittest.main()
