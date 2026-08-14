import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestDatabaseSecurity(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.__enter__()
        import uuid
        uname = f"sec_dev_{str(uuid.uuid4())[:8]}"
        email = f"{uname}@test.com"
        self.dev_payload = {"username": uname, "email": email, "password": "pass"}
        self.client.post("/api/v1/auth/register", json=self.dev_payload)
        login_res = self.client.post("/api/v1/auth/login", json={"email": email, "password": "pass"})
        self.token = login_res.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        import uuid
        slug = f"sec-proj-{str(uuid.uuid4())[:8]}"
        res = self.client.post("/api/v1/baas/projects/", json={"project_name": "Sec Proj", "project_slug": slug, "description": "Desc"}, headers=self.headers)
        self.project_id = res.json()["project_id"]

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_sql_injection_table_name(self):
        # Attempt to create a table with SQL injection payload in the table name
        payload = {
            "name": "users; DROP TABLE sqlite_master; --",
            "columns": {"id": "TEXT"}
        }
        res = self.client.post(f"/api/v1/baas/projects/{self.project_id}/tables", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 422) # Should fail Pydantic validation regex

    def test_sql_injection_column_name(self):
        # Attempt to create a table with SQL injection payload in a column name
        payload = {
            "name": "safe_table",
            "columns": {"valid_col": "TEXT", "bad_col; DROP TABLE safe_table; --": "TEXT"}
        }
        res = self.client.post(f"/api/v1/baas/projects/{self.project_id}/tables", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 422) # Should fail TenantDatabaseValidator

    def test_sql_injection_data_plane(self):
        # Create a valid table first
        self.client.post(f"/api/v1/baas/projects/{self.project_id}/tables", json={"name": "data_tbl", "columns": {"data": "TEXT"}}, headers=self.headers)
        
        # Get API key
        key_res = self.client.post(f"/api/v1/baas/projects/{self.project_id}/keys", json={"name": "test_key"}, headers=self.headers)
        api_key = key_res.json()["key"]
        
        # Malicious column name
        malicious_data = {
            "data": "valid_data",
            "invalid_col') VALUES ('hacked'); --": "hacked"
        }
        res = self.client.post(f"/api/v1/baas/projects/{self.project_id}/data/data_tbl", json=malicious_data, headers={"X-Project-API-Key": api_key})
        self.assertEqual(res.status_code, 422) # Validation should block malicious column names

    def test_oversized_query_payload(self):
        # Create a valid table
        self.client.post(f"/api/v1/baas/projects/{self.project_id}/tables", json={"name": "big_tbl", "columns": {"data": "TEXT"}}, headers=self.headers)
        
        # Get API key
        key_res = self.client.post(f"/api/v1/baas/projects/{self.project_id}/keys", json={"name": "test_key"}, headers=self.headers)
        api_key = key_res.json()["key"]
        
        # Large payload (~5MB string)
        huge_string = "A" * (5 * 1024 * 1024)
        large_payload = {"data": huge_string}
        
        res = self.client.post(f"/api/v1/baas/projects/{self.project_id}/data/big_tbl", json=large_payload, headers={"X-Project-API-Key": api_key})
        self.assertIn(res.status_code, [201, 413])

    def test_malicious_reserved_identifiers(self):
        # Try to access sqlite_master
        res = self.client.get(f"/api/v1/baas/projects/{self.project_id}/tables/sqlite_master", headers=self.headers)
        self.assertEqual(res.status_code, 422) # Protected by identifier regex / prefix validator
        
        payload = {
            "name": "sqlite_hacked",
            "columns": {"id": "TEXT"}
        }
        res2 = self.client.post(f"/api/v1/baas/projects/{self.project_id}/tables", json=payload, headers=self.headers)
        self.assertEqual(res2.status_code, 422)
