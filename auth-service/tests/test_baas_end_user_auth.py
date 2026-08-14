import unittest
import uuid
from fastapi.testclient import TestClient
from app.main import app

class TestBaaSEndUserAuth(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.__enter__()
        
        # 1. Register a developer
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
        
        # 2. Create Project A
        proj_a_slug = f"proj-a-{uuid.uuid4().hex[:8]}"
        res_a = self.client.post("/api/v1/baas/projects/", json={
            "project_name": "Project A",
            "project_slug": proj_a_slug,
            "description": "Project A for End User Tests"
        }, headers=self.dev_headers)
        self.proj_a_id = res_a.json()["project_id"]
        
        # 3. Create Project B
        proj_b_slug = f"proj-b-{uuid.uuid4().hex[:8]}"
        res_b = self.client.post("/api/v1/baas/projects/", json={
            "project_name": "Project B",
            "project_slug": proj_b_slug,
            "description": "Project B for End User Tests"
        }, headers=self.dev_headers)
        self.proj_b_id = res_b.json()["project_id"]

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_end_user_registration_and_login(self):
        end_user_email = f"enduser_{uuid.uuid4().hex[:8]}@example.com"
        
        # Register
        reg_res = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/register", json={
            "email": end_user_email,
            "password": "securepassword123"
        })
        self.assertEqual(reg_res.status_code, 201)
        
        # Login
        login_res = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/login", json={
            "email": end_user_email,
            "password": "securepassword123"
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("access_token", login_res.json())
        
        # Verify /me endpoint
        token = login_res.json()["access_token"]
        me_res = self.client.get(f"/api/v1/baas/projects/{self.proj_a_id}/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["email"], end_user_email)
        
    def test_project_isolation(self):
        end_user_email = f"enduser_{uuid.uuid4().hex[:8]}@example.com"
        
        # Register in Project A
        self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/register", json={
            "email": end_user_email,
            "password": "securepassword123"
        })
        
        # Try to login in Project B (should fail)
        login_res = self.client.post(f"/api/v1/baas/projects/{self.proj_b_id}/auth/login", json={
            "email": end_user_email,
            "password": "securepassword123"
        })
        self.assertEqual(login_res.status_code, 401)
        
        # Register in Project B (should succeed because isolation)
        reg_res_b = self.client.post(f"/api/v1/baas/projects/{self.proj_b_id}/auth/register", json={
            "email": end_user_email,
            "password": "securepassword123"
        })
        self.assertEqual(reg_res_b.status_code, 201)

    def test_token_boundary_developer_token_rejected(self):
        # Developer tries to access End User /me
        me_res = self.client.get(f"/api/v1/baas/projects/{self.proj_a_id}/auth/me", headers=self.dev_headers)
        self.assertEqual(me_res.status_code, 401, "Developer token should be rejected on End-User routes")

    def test_token_boundary_end_user_token_rejected_on_control_plane(self):
        end_user_email = f"enduser_{uuid.uuid4().hex[:8]}@example.com"
        self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/register", json={
            "email": end_user_email,
            "password": "securepassword123"
        })
        login_res = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/login", json={
            "email": end_user_email,
            "password": "securepassword123"
        })
        end_user_token = login_res.json()["access_token"]
        
        # End user tries to hit Developer Control Plane (e.g., list projects)
        res = self.client.get("/api/v1/baas/projects/", headers={"Authorization": f"Bearer {end_user_token}"})
        self.assertEqual(res.status_code, 401, "End-User token should be rejected on Control Plane")

    def test_password_reset_and_email_verification_flows(self):
        from app.api.baas_auth_routes import get_baas_auth_service
        baas_auth_service = self.client.app.dependency_overrides[get_baas_auth_service]()
        email_provider = baas_auth_service._email_provider
        email_provider.sent_emails.clear()

        end_user_email = f"enduser_{uuid.uuid4().hex[:8]}@example.com"
        
        # 1. Registration should trigger verification email
        res = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/register", json={
            "email": end_user_email,
            "password": "securepassword123"
        })
        self.assertEqual(res.status_code, 201)
        
        self.assertEqual(len(email_provider.sent_emails), 1)
        verif_email = email_provider.sent_emails[0]
        self.assertEqual(verif_email["type"], "verification")
        verif_token = verif_email["token"]
        
        # 2. Test verify email
        verify_res = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/verify-email", json={
            "verification_token": verif_token
        })
        self.assertEqual(verify_res.status_code, 200)
        
        # 3. Test verification token is single-use
        verify_res2 = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/verify-email", json={
            "verification_token": verif_token
        })
        self.assertNotEqual(verify_res2.status_code, 200) # Should be 401 or 400
        
        email_provider.sent_emails.clear()

        # 4. Request password reset
        reset_req_res = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/reset-password-request", json={
            "email": end_user_email
        })
        self.assertEqual(reset_req_res.status_code, 200)
        
        self.assertEqual(len(email_provider.sent_emails), 1)
        reset_email = email_provider.sent_emails[0]
        self.assertEqual(reset_email["type"], "password_reset")
        reset_token = reset_email["token"]
        
        # 5. Confirm password reset
        reset_res = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/reset-password", json={
            "reset_token": reset_token,
            "new_password": "newsecurepassword123"
        })
        self.assertEqual(reset_res.status_code, 200)
        
        # 6. Test reset token is single-use
        reset_res2 = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/reset-password", json={
            "reset_token": reset_token,
            "new_password": "newsecurepassword1234"
        })
        self.assertNotEqual(reset_res2.status_code, 200) # Should be 401 or 400
        
        # 7. Test login with new password works
        login_res = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/login", json={
            "email": end_user_email,
            "password": "newsecurepassword123"
        })
        self.assertEqual(login_res.status_code, 200)
        
        # 8. Test enumeration protection (request reset for non-existent email)
        email_provider.sent_emails.clear()
        fake_reset_req = self.client.post(f"/api/v1/baas/projects/{self.proj_a_id}/auth/reset-password-request", json={
            "email": "doesntexist@example.com"
        })
        self.assertEqual(fake_reset_req.status_code, 200)
        self.assertEqual(len(email_provider.sent_emails), 0)
