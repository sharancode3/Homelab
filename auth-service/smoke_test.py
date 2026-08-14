import httpx
import time

BASE_URL = "http://127.0.0.1:8003/api/v1"

def run_smoke_test():
    print("1. Registering developers...")
    # Register Dev A
    httpx.post(f"{BASE_URL}/auth/register", json={
        "username": "dev_a_smoke", "email": "a@smoke.com", "password": "pass"
    })
    # Login Dev A
    res_a = httpx.post(f"{BASE_URL}/auth/login", json={"email": "a@smoke.com", "password": "pass"})
    token_a = res_a.json()["access_token"]
    
    # Register Dev B
    httpx.post(f"{BASE_URL}/auth/register", json={
        "username": "dev_b_smoke", "email": "b@smoke.com", "password": "pass"
    })
    res_b = httpx.post(f"{BASE_URL}/auth/login", json={"email": "b@smoke.com", "password": "pass"})
    token_b = res_b.json()["access_token"]
    
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    print("2. Dev A creates Project A1...")
    p_a1 = httpx.post(f"{BASE_URL}/baas/projects/", json={"project_name": "A1", "project_slug": f"smoke-a1-{int(time.time())}"}, headers=headers_a)
    id_a1 = p_a1.json()["project_id"]
    
    print("3. Dev B creates Project B1...")
    p_b1 = httpx.post(f"{BASE_URL}/baas/projects/", json={"project_name": "B1", "project_slug": f"smoke-b1-{int(time.time())}"}, headers=headers_b)
    id_b1 = p_b1.json()["project_id"]
    
    print("4. Dev A lists projects...")
    list_a = httpx.get(f"{BASE_URL}/baas/projects/", headers=headers_a).json()
    ids_a = [p["project_id"] for p in list_a]
    assert id_a1 in ids_a
    assert id_b1 not in ids_a
    
    print("5. Dev A attempts IDOR on Project B1...")
    idor = httpx.get(f"{BASE_URL}/baas/projects/{id_b1}", headers=headers_a)
    assert idor.status_code == 403, f"Expected 403, got {idor.status_code}"
    
    print("6. Verifying legacy route is protected...")
    legacy_res = httpx.post(f"{BASE_URL}/projects/register", json={
        "project_id": f"proj_{int(time.time())}", "project_name": "Legacy", "project_slug": "legacy", "project_type": "standard", "project_version": "1.0.0"
    })
    assert legacy_res.status_code == 403, f"Expected 403, got {legacy_res.status_code}"
    
    print("7. Verifying legacy route works with internal token...")
    internal_headers = {"X-Internal-Token": "my-secret"}
    legacy_internal_res = httpx.post(f"{BASE_URL}/projects/register", json={
        "project_id": f"proj_{int(time.time())}", "project_name": "Legacy", "project_slug": f"legacy-{int(time.time())}", "project_type": "standard", "project_version": "1.0.0"
    }, headers=internal_headers)
    assert legacy_internal_res.status_code == 200, f"Expected 200, got {legacy_internal_res.status_code} - {legacy_internal_res.text}"
    
    print("8. Verifying BaaS Deploy Proxy works...")
    deploy_res = httpx.post(f"{BASE_URL}/baas/projects/{id_a1}/deploy", json={
        "requested_by": "dev_a_smoke"
    }, headers=headers_a)
    assert deploy_res.status_code == 200, f"Expected 200, got {deploy_res.status_code}"
    assert deploy_res.json()["status"] == "completed"

    print("Smoke test PASSED!")

if __name__ == "__main__":
    run_smoke_test()
