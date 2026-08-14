from datetime import datetime
import unittest
from fastapi import HTTPException
from app.api.baas_service import BaaSProjectServiceLayer
from app.api.service import APIServiceLayer
from app.project_registry_manager import ProjectRegistryManager
from app.storage.providers.sqlite import SQLiteProjectAuthorizationRepository
from app.identity.models import DeveloperUser
from app.api.baas_models import BaaSProjectCreateRequest
from unittest.mock import MagicMock

class MockUserRepository:
    def __init__(self):
        self.users = {
            "u1": DeveloperUser(user_id="u1", username="owner", email="owner@x.com", hashed_password="", created_at=datetime.utcnow()),
            "u2": DeveloperUser(user_id="u2", username="admin", email="admin@x.com", hashed_password="", created_at=datetime.utcnow()),
            "u3": DeveloperUser(user_id="u3", username="dev", email="dev@x.com", hashed_password="", created_at=datetime.utcnow()),
            "u4": DeveloperUser(user_id="u4", username="viewer", email="viewer@x.com", hashed_password="", created_at=datetime.utcnow()),
        }
        self.by_email = {u.email: u for u in self.users.values()}

    def get_by_user_id(self, user_id):
        return self.users.get(user_id)

    def get_by_email(self, email):
        return self.by_email.get(email)

class TestBaaSRBAC(unittest.TestCase):
    def setUp(self):
        self.authz_repo = SQLiteProjectAuthorizationRepository(db_path=":memory:")
        self.registry = MagicMock(spec=ProjectRegistryManager)
        self.internal_service = MagicMock(spec=APIServiceLayer)
        self.user_repo = MockUserRepository()
        self.service = BaaSProjectServiceLayer(
            self.internal_service, self.authz_repo, self.registry, self.user_repo
        )
        
        self.registry.get_by_project_id.return_value = MagicMock(
            project_id="proj_11112222", project_name="T", project_slug="t", project_type=MagicMock(value="backend"), status=MagicMock(value="registered"), project_version="1"
        )
        self.project_id = "proj_11112222"
        self.authz_repo.add_member(self.project_id, "u1", "owner")
        self.authz_repo.add_member(self.project_id, "u2", "admin")
        self.authz_repo.add_member(self.project_id, "u3", "developer")
        self.authz_repo.add_member(self.project_id, "u4", "viewer")

    def test_list_members(self):
        members = self.service.list_members(self.project_id)
        self.assertEqual(len(members), 4)

    def test_admin_add_developer(self):
        # Create a new user to add
        self.user_repo.users["u5"] = DeveloperUser(user_id="u5", username="new", email="new@x.com", hashed_password="", created_at=datetime.utcnow())
        self.user_repo.by_email["new@x.com"] = self.user_repo.users["u5"]
        
        res = self.service.add_member(self.project_id, "new@x.com", "developer", "admin")
        self.assertEqual(res["role"], "developer")
        self.assertEqual(res["user_id"], "u5")
        
    def test_admin_add_owner_fails(self):
        self.user_repo.users["u5"] = DeveloperUser(user_id="u5", username="new", email="new@x.com", hashed_password="", created_at=datetime.utcnow())
        self.user_repo.by_email["new@x.com"] = self.user_repo.users["u5"]
        
        with self.assertRaises(HTTPException) as cm:
            self.service.add_member(self.project_id, "new@x.com", "owner", "admin")
        self.assertEqual(cm.exception.status_code, 403)

    def test_owner_add_owner_succeeds(self):
        self.user_repo.users["u5"] = DeveloperUser(user_id="u5", username="new", email="new@x.com", hashed_password="", created_at=datetime.utcnow())
        self.user_repo.by_email["new@x.com"] = self.user_repo.users["u5"]
        
        res = self.service.add_member(self.project_id, "new@x.com", "owner", "owner")
        self.assertEqual(res["role"], "owner")

    def test_admin_remove_developer(self):
        self.service.remove_member(self.project_id, "u3", "admin")
        self.assertIsNone(self.authz_repo.get_role(self.project_id, "u3"))

    def test_admin_remove_owner_fails(self):
        with self.assertRaises(HTTPException) as cm:
            self.service.remove_member(self.project_id, "u1", "admin")
        self.assertEqual(cm.exception.status_code, 403)

    def test_owner_remove_last_owner_fails(self):
        with self.assertRaises(HTTPException) as cm:
            self.service.remove_member(self.project_id, "u1", "owner")
        self.assertEqual(cm.exception.status_code, 400)

    def test_owner_demote_last_owner_fails(self):
        with self.assertRaises(HTTPException) as cm:
            self.service.update_member_role(self.project_id, "u1", "admin", "owner")
        self.assertEqual(cm.exception.status_code, 400)

    def test_owner_remove_owner_when_multiple_succeeds(self):
        self.user_repo.users["u5"] = DeveloperUser(user_id="u5", username="new", email="new@x.com", hashed_password="", created_at=datetime.utcnow())
        self.user_repo.by_email["new@x.com"] = self.user_repo.users["u5"]
        self.service.add_member(self.project_id, "new@x.com", "owner", "owner")
        
        # Now there are 2 owners. u1 should be able to remove u5.
        self.service.remove_member(self.project_id, "u5", "owner")
        self.assertIsNone(self.authz_repo.get_role(self.project_id, "u5"))

    def test_admin_modify_owner_fails(self):
        with self.assertRaises(HTTPException) as cm:
            self.service.update_member_role(self.project_id, "u1", "developer", "admin")
        self.assertEqual(cm.exception.status_code, 403)
        
    def test_admin_promote_developer_to_owner_fails(self):
        with self.assertRaises(HTTPException) as cm:
            self.service.update_member_role(self.project_id, "u3", "owner", "admin")
        self.assertEqual(cm.exception.status_code, 403)

    def test_duplicate_member_rejected(self):
        with self.assertRaises(HTTPException) as cm:
            self.service.add_member(self.project_id, "dev@x.com", "viewer", "owner")
        self.assertEqual(cm.exception.status_code, 400)

    def test_nonexistent_email_rejected(self):
        with self.assertRaises(HTTPException) as cm:
            self.service.add_member(self.project_id, "nobody@x.com", "viewer", "owner")
        self.assertEqual(cm.exception.status_code, 404)

if __name__ == "__main__":
    unittest.main()
