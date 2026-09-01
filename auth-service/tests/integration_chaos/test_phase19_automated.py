import os
import shutil
import tempfile
import uuid
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.config.settings import config
from app.services.email_service import MockEmailProvider
from app.storage.providers.sqlite_tenant import BaaSStorageRepository

class TestPhase19ChaosAutomated(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.__enter__()
        
        # 1. Register a developer and login
        dev_email = f"dev_{uuid.uuid4().hex[:8]}@test.com"
        self.client.post("/api/v1/auth/register", json={
            "username": f"dev_{uuid.uuid4().hex[:8]}",
            "email": dev_email,
            "password": "password123"
        })
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": dev_email,
            "password": "password123"
        })
        self.dev_token = login_res.json()["access_token"]
        self.dev_headers = {"Authorization": f"Bearer {self.dev_token}"}
        
        # 2. Create a project
        self.proj_slug = f"proj-{uuid.uuid4().hex[:8]}"
        res = self.client.post("/api/v1/baas/projects/", json={
            "project_name": "Phase 19 Test Project",
            "project_slug": self.proj_slug,
            "description": "Chaos Testing"
        }, headers=self.dev_headers)
        self.project_id = res.json()["project_id"]

        # 3. Create API Key
        res_key = self.client.post(f"/api/v1/baas/projects/{self.project_id}/keys", json={
            "name": "chaos key"
        }, headers=self.dev_headers)
        self.api_key = res_key.json()["key"]
        
        # Isolation: temporary directory for storage
        self.temp_storage = tempfile.mkdtemp()
        self.original_storage_path = config.storage_path
        config.storage_path = self.temp_storage

    def tearDown(self):
        config.storage_path = self.original_storage_path
        shutil.rmtree(self.temp_storage, ignore_errors=True)
        self.client.__exit__(None, None, None)
        
    def test_scenario_5_storage_write_fails(self):
        """
        Scenario 5: Storage Write Fails
        Discrepancy Documented: Currently unexpected storage exceptions map to 400 Bad Request, not 500.
        """
        auth_headers = {"X-Project-API-Key": self.api_key}
        
        # Precondition: Verify DB state (0 files) and normal upload succeeds
        list_res = self.client.get(f"/api/v1/baas/projects/{self.project_id}/storage/", headers=auth_headers)
        self.assertEqual(len(list_res.json()), 0)
        
        from app.providers.storage.exceptions import ArtifactWriteError
        
        with patch('app.providers.storage.local_storage.LocalStorageProvider.create_artifact_stream') as mock_create:
            # Induce Failure: Storage adapter throws write error
            mock_create.side_effect = ArtifactWriteError("Simulated disk full or permission denied")
            
            # Attempt write
            upload_res = self.client.post(
                f"/api/v1/baas/projects/{self.project_id}/storage/",
                headers=auth_headers,
                files={"file": ("test.txt", b"chaos content", "text/plain")}
            )
            
            # Verify Error Behavior: Current contract maps to 400 Bad Request
            self.assertEqual(upload_res.status_code, 400)
            
            # Verify No Leakage: Stack trace/filesystem paths should not be in the response
            detail = upload_res.json().get("detail", "")
            self.assertNotIn(self.temp_storage, detail)
            self.assertNotIn("Traceback", detail)
            
            # Verify State Integrity: No orphaned DB metadata
            list_res_after = self.client.get(f"/api/v1/baas/projects/{self.project_id}/storage/", headers=auth_headers)
            self.assertEqual(len(list_res_after.json()), 0)
            
        # Context manager exits, patch is removed -> Recovery.
        
        # Verify Recovery: Normal upload works again using the real adapter
        upload_res_recovery = self.client.post(
            f"/api/v1/baas/projects/{self.project_id}/storage/",
            headers=auth_headers,
            files={"file": ("test.txt", b"chaos content", "text/plain")}
        )
        self.assertEqual(upload_res_recovery.status_code, 201)
        list_res_final = self.client.get(f"/api/v1/baas/projects/{self.project_id}/storage/", headers=auth_headers)
        self.assertEqual(len(list_res_final.json()), 1)

    def test_scenario_6_backup_fails(self):
        """
        Scenario 6: Backup Fails
        Uses mock because engine does not currently use physical storage adapter.
        """
        from app.platform.backup.exceptions import BackupException
        from app.api.routes import get_api_service
        
        # Extract the dynamically created backup engine from the FastAPI app instance
        api_service = self.client.app.dependency_overrides[get_api_service]()
        backup_engine = api_service._coordinator._backup_engine
        
        original_backup = backup_engine.backup
        
        def mock_backup_func(*args, **kwargs):
            raise BackupException("Injected mock backup engine failure")
            
        backup_engine.backup = mock_backup_func
        
        try:
            # Initiate backup
            res = self.client.post(f"/api/v1/baas/projects/{self.project_id}/backup", json={
                "backup_type": "full"
            }, headers=self.dev_headers)
            self.assertEqual(res.status_code, 200)
            op_id = res.json()["operation_id"]
        
            # Wait for operation to complete (sync/async depending on architecture)
            import time
            max_wait = 10
            for _ in range(max_wait):
                history_res = self.client.get(f"/api/v1/baas/projects/{self.project_id}/history", headers=self.dev_headers)
                history = history_res.json()["history"]
                op = next((o for o in history if o["operation_id"] == op_id), None)
                if op and op["status"] in ["failed", "completed"]:
                    break
                time.sleep(0.1)
        
            # Verify it failed
            self.assertIsNotNone(op)
            if op:
                self.assertEqual(op["status"], "failed")
                self.assertIn("Injected mock backup engine failure", str(op.get("failures", [])))
                
        finally:
            backup_engine.backup = original_backup
            
        # Verify State Integrity: The project can still be validated
        val_res = self.client.post(f"/api/v1/baas/projects/{self.project_id}/validate", headers=self.dev_headers)
        self.assertEqual(val_res.status_code, 200, f"Validate failed with {val_res.status_code}: {val_res.text}")
        self.assertTrue(val_res.json()["is_valid"])

    def test_scenario_7_restore_fails(self):
        """
        Scenario 7: Restore Fails
        """
        # Create a valid backup
        res = self.client.post(f"/api/v1/baas/projects/{self.project_id}/backup", json={
            "backup_type": "full"
        }, headers=self.dev_headers)
        self.assertEqual(res.status_code, 200)
        
        import time
        time.sleep(1) # wait for backup to simulate
        
        # Manually alter the project state
        with patch('app.platform.backup.engine.BackupEngine._verify_manifest_integrity') as mock_verify:
            mock_verify.return_value = False # Force validation failure
            
            # Attempt restore
            res_restore = self.client.post(f"/api/v1/baas/projects/{self.project_id}/restore", json={
                "backup_id": "test_invalid_backup_id"
            }, headers=self.dev_headers)
            
            # Assert cleanly aborts
            # Depending on if it's async or sync, it may return 200 then fail, or 400
            if res_restore.status_code == 200:
                op_id = res_restore.json()["operation_id"]
                for _ in range(10):
                    history_res = self.client.get(f"/api/v1/baas/projects/{self.project_id}/history", headers=self.dev_headers)
                    history = history_res.json()["history"]
                    op = next((o for o in history if o["operation_id"] == op_id), None)
                    if op and op["status"] in ["failed", "completed"]:
                        break
                    time.sleep(0.1)
                self.assertEqual(op["status"], "failed")
            else:
                self.assertNotEqual(res_restore.status_code, 200)

    @patch('app.services.email_service.MockEmailProvider.send_verification_email')
    def test_scenario_8_email_provider_unavailable(self, mock_email):
        """
        Scenario 8: Email Provider Unavailable
        Documents discrepancy: Synchronous email failure yields 400 Bad Request, but account is created.
        """
        email_to_fail = f"enduser_{uuid.uuid4().hex[:8]}@test.com"
        
        from app.services.email_service import EmailDeliveryException
        mock_email.side_effect = EmailDeliveryException("Failed to send email. Please try again later.")

        # Attempt registration
        res = self.client.post(f"/api/v1/baas/projects/{self.project_id}/auth/register", json={
            "email": email_to_fail,
            "password": "password123"
        }, headers={"X-Project-API-Key": self.api_key})
        
        # Verify Error Behavior: The API returns a 400 due to existing sync contract
        self.assertEqual(res.status_code, 400)
        
        # Verify State Integrity: Even though it returned 400, the user was committed.
        mock_email.side_effect = None # Recover
        
        res_dup = self.client.post(f"/api/v1/baas/projects/{self.project_id}/auth/register", json={
            "email": email_to_fail,
            "password": "password123"
        }, headers={"X-Project-API-Key": self.api_key})
        
        self.assertEqual(res_dup.status_code, 409) # 409 means the user already exists, proving state wasn't rolled back

    def test_scenario_9_invalid_api_key(self):
        """
        Scenario 9: Invalid API Key
        """
        invalid_key = "pk_live_wrongid_wrongsecret"
        
        res = self.client.get(f"/api/v1/baas/projects/{self.project_id}/storage/", headers={
            "X-Project-API-Key": invalid_key
        })
        
        # Expected Error
        self.assertEqual(res.status_code, 401)
        
        # State Integrity
        # No modification could have happened

if __name__ == "__main__":
    unittest.main()
