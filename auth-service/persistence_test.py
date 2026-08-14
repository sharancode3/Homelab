import httpx

BASE_URL = "http://127.0.0.1:8003/api/v1"

def run_persistence_test():
    print("1. Login Dev A...")
    res_a = httpx.post(f"{BASE_URL}/auth/login", json={"email": "a@smoke.com", "password": "pass"})
    token_a = res_a.json()["access_token"]
    
    print("2. Login Dev B...")
    res_b = httpx.post(f"{BASE_URL}/auth/login", json={"email": "b@smoke.com", "password": "pass"})
    token_b = res_b.json()["access_token"]
    
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    print("3. Dev A lists projects...")
    list_a = httpx.get(f"{BASE_URL}/baas/projects/", headers=headers_a).json()
    ids_a = [p["project_name"] for p in list_a]
    assert "A1" in ids_a, "A1 not found in Dev A projects"
    assert "B1" not in ids_a, "B1 leaked into Dev A projects"
    print("Dev A projects:", ids_a)
    
    print("4. Dev B lists projects...")
    list_b = httpx.get(f"{BASE_URL}/baas/projects/", headers=headers_b).json()
    ids_b = [p["project_name"] for p in list_b]
    assert "B1" in ids_b, "B1 not found in Dev B projects"
    assert "A1" not in ids_b, "A1 leaked into Dev B projects"
    print("Dev B projects:", ids_b)
    
    print("Persistence test PASSED!")

if __name__ == "__main__":
    run_persistence_test()
