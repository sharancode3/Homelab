import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.api.rate_limiter import rate_limit_ip, rate_limit_api_key

class TestBaaSProjects(unittest.TestCase):
    def create_user_and_login(self, client: TestClient, username: str, email: str, password: str = "password123") -> str:
        client.post("/api/v1/auth/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        response = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        return response.json()["access_token"]

    def test_baas_project_creation_authenticated(self):
        with TestClient(app) as client:
            token = self.create_user_and_login(client, "dev_a", "dev_a@example.com")
            headers = {"Authorization": f"Bearer {token}"}
            
            response = client.post("/api/v1/baas/projects/", json={
                "project_name": "Test Project A",
                "project_slug": f"test-project-a-{__import__('uuid').uuid4().hex}"
            }, headers=headers)
            
            self.assertEqual(response.status_code, 201)
            data = response.json()
            self.assertIn("project_id", data)
            self.assertEqual(data["project_name"], "Test Project A")
            
    def test_baas_project_creation_unauthenticated(self):
        with TestClient(app) as client:
            response = client.post("/api/v1/baas/projects/", json={
                "project_name": "Test Project B",
                "project_slug": f"test-project-b-{__import__('uuid').uuid4().hex}"
            })
            self.assertEqual(response.status_code, 401)
        
    def test_baas_project_isolation_and_idor(self):
        with TestClient(app) as client:
            token_a = self.create_user_and_login(client, "user_a", "user_a@test.com")
            token_b = self.create_user_and_login(client, "user_b", "user_b@test.com")
            
            headers_a = {"Authorization": f"Bearer {token_a}"}
            headers_b = {"Authorization": f"Bearer {token_b}"}
            
            # User A creates a project
            res_a = client.post("/api/v1/baas/projects/", json={
                "project_name": "Project A",
                "project_slug": f"project-a-{__import__("uuid").uuid4().hex}"
            }, headers=headers_a)
            self.assertEqual(res_a.status_code, 201)
            proj_a_id = res_a.json()["project_id"]
            
            # User B creates a project
            res_b = client.post("/api/v1/baas/projects/", json={
                "project_name": "Project B",
                "project_slug": f"project-b-{__import__('uuid').uuid4().hex}"
            }, headers=headers_b)
            self.assertEqual(res_b.status_code, 201)
            proj_b_id = res_b.json()["project_id"]
            
            # User A lists projects, should only see Project A
            list_a = client.get("/api/v1/baas/projects/", headers=headers_a)
            self.assertEqual(list_a.status_code, 200)
            ids_a = [p["project_id"] for p in list_a.json()]
            self.assertIn(proj_a_id, ids_a)
            self.assertNotIn(proj_b_id, ids_a)
            
            # User B lists projects, should only see Project B
            list_b = client.get("/api/v1/baas/projects/", headers=headers_b)
            self.assertEqual(list_b.status_code, 200)
            ids_b = [p["project_id"] for p in list_b.json()]
            self.assertIn(proj_b_id, ids_b)
            self.assertNotIn(proj_a_id, ids_b)
            
            # IDOR Test: User A tries to get Project B
            idor_res = client.get(f"/api/v1/baas/projects/{proj_b_id}", headers=headers_a)
            self.assertEqual(idor_res.status_code, 403)
            
            # Normal Access: User A gets Project A
            norm_res = client.get(f"/api/v1/baas/projects/{proj_a_id}", headers=headers_a)
            self.assertEqual(norm_res.status_code, 200)
            self.assertEqual(norm_res.json()["project_name"], "Project A")
