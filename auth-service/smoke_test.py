import time
import httpx


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

    # We need user IDs. Let's get them from the token or an endpoint if available.
    # Actually, let's just GET /auth/me
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    user_a = httpx.get(f"{BASE_URL}/auth/me", headers=headers_a).json()
    user_b = httpx.get(f"{BASE_URL}/auth/me", headers=headers_b).json()
    user_id_a = user_a["user_id"]
    user_id_b = user_b["user_id"]


    print("2. Dev A creates Project A1...")
    p_a1 = httpx.post(f"{BASE_URL}/baas/projects/", json={"project_name": "A1", "project_slug": f"smoke-a1-{int(time.time())}"}, headers=headers_a)
    proj_a_id = p_a1.json()["project_id"]

    print("3. Dev B creates Project B1...")
    p_b1 = httpx.post(f"{BASE_URL}/baas/projects/", json={"project_name": "B1", "project_slug": f"smoke-b1-{int(time.time())}"}, headers=headers_b)
    proj_b_id = p_b1.json()["project_id"]

    print("4. Dev A lists projects...")
    list_a = httpx.get(f"{BASE_URL}/baas/projects/", headers=headers_a).json()
    ids_a = [p["project_id"] for p in list_a]
    assert proj_a_id in ids_a
    assert proj_b_id not in ids_a

    print("5. Dev A attempts IDOR on Project B1...")
    idor = httpx.get(f"{BASE_URL}/baas/projects/{proj_b_id}", headers=headers_a)
    assert idor.status_code == 403, f"Expected 403, got {idor.status_code}"

    print("6. Verifying legacy route is protected...")
    legacy_res = httpx.post(f"{BASE_URL}/projects/register", json={
        "project_id": f"proj_{int(time.time())}", "project_name": "Test", "project_slug": f"test-{int(time.time())}", "project_type": "standard", "project_version": "1.0.0"
    })
    assert legacy_res.status_code in (403, 422), f"Expected 403 or 422, got {legacy_res.status_code}"

    print("7. Verifying legacy route works with internal token...")
    legacy_internal_res = httpx.post(f"{BASE_URL}/projects/register", json={
        "project_id": f"proj_{int(time.time())}", "project_name": "Test", "project_slug": f"test-{int(time.time())}", "project_type": "standard", "project_version": "1.0.0"
    }, headers={"X-Internal-Token": "my-secret", "Content-Type": "application/json"})
    assert legacy_internal_res.status_code == 200, f"Expected 200, got {legacy_internal_res.status_code} - {legacy_internal_res.text}"

    print("8. Verifying BaaS Deploy Proxy works...")
    deploy_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/deploy", json={
        "requested_by": "dev_a_smoke"
    }, headers=headers_a)
    assert deploy_res.status_code == 200, f"Expected 200, got {deploy_res.status_code}"

    print("9. RBAC - Developer A (Owner) adds Developer B as Developer...")
    add_member_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/members", json={
        "email": "b@smoke.com", "role": "developer"
    }, headers=headers_a)
    assert add_member_res.status_code == 200, f"Expected 200, got {add_member_res.status_code}"

    print("10. RBAC - Developer B (Developer) attempts read/deploy...")
    get_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}", headers=headers_b)
    assert get_res.status_code == 200, f"Expected 200, got {get_res.status_code}"

    deploy_b_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/deploy", json={"requested_by": "dev_b_smoke"}, headers=headers_b)
    assert deploy_b_res.status_code == 200, f"Expected 200, got {deploy_b_res.status_code}"

    print("11. RBAC - Developer B (Developer) attempts backup (DENIED)...")
    backup_b_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/backup", json={"requested_by": "dev_b_smoke"}, headers=headers_b)
    assert backup_b_res.status_code == 403, f"Expected 403, got {backup_b_res.status_code}"

    print("12. RBAC - Developer A promotes Developer B to Admin...")
    update_role_res = httpx.put(f"{BASE_URL}/baas/projects/{proj_a_id}/members/{user_id_b}", json={"role": "admin"}, headers=headers_a)
    assert update_role_res.status_code == 200, f"Expected 200, got {update_role_res.status_code}"

    print("13. RBAC - Developer B (Admin) attempts backup (ALLOWED)...")
    backup_b_res2 = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/backup", json={"requested_by": "dev_b_smoke"}, headers=headers_b)
    assert backup_b_res2.status_code == 200, f"Expected 200, got {backup_b_res2.status_code}"

    print("14. RBAC - Developer B (Admin) attempts to add an Owner (DENIED)...")
    dev_c = {"username": "dev_c_smoke", "email": f"dev_c_smoke_{int(time.time())}@example.com", "password": "password123"}
    httpx.post(f"{BASE_URL}/auth/register", json=dev_c)
    add_owner_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/members", json={"email": dev_c["email"], "role": "owner"}, headers=headers_b)
    assert add_owner_res.status_code == 403, f"Expected 403, got {add_owner_res.status_code}"

    print("15. RBAC - Developer B (Admin) attempts to demote Developer A (Owner) (DENIED)...")
    demote_owner_res = httpx.put(f"{BASE_URL}/baas/projects/{proj_a_id}/members/{user_id_a}", json={"role": "admin"}, headers=headers_b)
    assert demote_owner_res.status_code == 403, f"Expected 403, got {demote_owner_res.status_code}"

    print("16. RBAC - Developer A (Owner) demotes themselves (Last Owner) (DENIED)...")
    demote_self_res = httpx.put(f"{BASE_URL}/baas/projects/{proj_a_id}/members/{user_id_a}", json={"role": "admin"}, headers=headers_a)
    assert demote_self_res.status_code == 400, f"Expected 400, got {demote_self_res.status_code}"

    print("17. RBAC - Developer A promotes Developer B to Owner...")
    promote_owner_res = httpx.put(f"{BASE_URL}/baas/projects/{proj_a_id}/members/{user_id_b}", json={"role": "owner"}, headers=headers_a)
    assert promote_owner_res.status_code == 200, f"Expected 200, got {promote_owner_res.status_code}"

    print("18. RBAC - Developer A removes Developer B (Allowed because 2 owners exist)...")
    remove_owner_res = httpx.delete(f"{BASE_URL}/baas/projects/{proj_a_id}/members/{user_id_b}", headers=headers_a)
    assert remove_owner_res.status_code == 204, f"Expected 204, got {remove_owner_res.status_code}"



    print("19. Generate API Key for Project A1...")
    key_a_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/keys", json={"name": "Test Key A"}, headers=headers_a)
    assert key_a_res.status_code == 200, f"Expected 200, got {key_a_res.status_code}"
    key_a = key_a_res.json()["key"]
    key_id_a = key_a_res.json()["key_id"]

    print("20. Generate API Key for Project B1...")
    key_b_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_b_id}/keys", json={"name": "Test Key B"}, headers=headers_b)
    assert key_b_res.status_code == 200, f"Expected 200, got {key_b_res.status_code}"
    key_b = key_b_res.json()["key"]
    key_id_b = key_b_res.json()["key_id"]

    print("21. B key against Project B (data-plane) → allowed.")
    dp_b = httpx.get(f"{BASE_URL}/baas/projects/{proj_b_id}/data/test", headers={"X-Project-API-Key": key_b})
    assert dp_b.status_code == 200, f"Expected 200, got {dp_b.status_code}"

    print("22. B key against Project A (data-plane) → denied.")
    dp_b_on_a = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/test", headers={"X-Project-API-Key": key_b})
    assert dp_b_on_a.status_code == 403, f"Expected 403, got {dp_b_on_a.status_code}"

    print("23. Revoke A key.")
    revoke_a = httpx.delete(f"{BASE_URL}/baas/projects/{proj_a_id}/keys/{key_id_a}", headers=headers_a)
    assert revoke_a.status_code == 204, f"Expected 204, got {revoke_a.status_code}"

    print("24. A key against Project A (data-plane) → denied.")
    dp_a_on_a = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/test", headers={"X-Project-API-Key": key_a})
    assert dp_a_on_a.status_code == 401, f"Expected 401, got {dp_a_on_a.status_code}"

    print("25. Rotate A key.")
    rotate_a = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/keys/{key_id_a}/rotate", headers=headers_a)
    assert rotate_a.status_code == 200, f"Expected 200, got {rotate_a.status_code}"
    new_key_a = rotate_a.json()["key"]

    print("26. New key A against Project A (data-plane) → allowed.")
    dp_new_a_on_a = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/test", headers={"X-Project-API-Key": new_key_a})
    assert dp_new_a_on_a.status_code == 200, f"Expected 200, got {dp_new_a_on_a.status_code}"

    print("27. API key against project/member/key management → denied.")
    members_with_api_key = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/members", headers={"X-Project-API-Key": new_key_a})
    assert members_with_api_key.status_code in (401, 403), f"Expected 401/403, got {members_with_api_key.status_code}"

    print("28. API key against deploy/backup/restore/validate → denied.")
    deploy_with_api_key = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/deploy", json={"requested_by": "api_key"}, headers={"X-Project-API-Key": new_key_a})
    assert deploy_with_api_key.status_code in (401, 403), f"Expected 401/403, got {deploy_with_api_key.status_code}"

    print("29. API key against legacy /api/v1/projects/* → denied.")

    legacy_with_api_key = httpx.post(f"{BASE_URL}/projects/register", json={
        "project_id": f"proj_{int(time.time())}", "project_name": "T", "project_slug": f"t-{int(time.time())}", "project_type": "s", "project_version": "1"
    }, headers={"X-Project-API-Key": new_key_a, "Content-Type": "application/json"})
    assert legacy_with_api_key.status_code in (401, 403, 422), f"Expected 401/403/422, got {legacy_with_api_key.status_code}"

    print("Smoke test PASSED!")

if __name__ == "__main__":
    run_smoke_test()
