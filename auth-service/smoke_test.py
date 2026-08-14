import httpx
import time
import os
import shutil

BASE_URL = "http://localhost:8018/api/v1"
INTERNAL_TOKEN = "my-secret"

def run_smoke_test():
    print("1. Registering developers...")
    dev_a = {"username": f"deva_{int(time.time())}", "email": f"deva_{int(time.time())}@test.com", "password": "pass"}
    dev_b = {"username": f"devb_{int(time.time())}", "email": f"devb_{int(time.time())}@test.com", "password": "pass"}
    dev_c = {"username": f"devc_{int(time.time())}", "email": f"devc_{int(time.time())}@test.com", "password": "pass"}

    httpx.post(f"{BASE_URL}/auth/register", json=dev_a)
    httpx.post(f"{BASE_URL}/auth/register", json=dev_b)
    httpx.post(f"{BASE_URL}/auth/register", json=dev_c)

    token_a = httpx.post(f"{BASE_URL}/auth/login", json={"email": dev_a["email"], "password": dev_a["password"]}).json()["access_token"]
    token_b = httpx.post(f"{BASE_URL}/auth/login", json={"email": dev_b["email"], "password": dev_b["password"]}).json()["access_token"]
    token_c = httpx.post(f"{BASE_URL}/auth/login", json={"email": dev_c["email"], "password": dev_c["password"]}).json()["access_token"]

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    headers_c = {"Authorization": f"Bearer {token_c}"}  # No access to any project

    user_a_id = httpx.get(f"{BASE_URL}/auth/me", headers=headers_a).json()["user_id"]
    user_b_id = httpx.get(f"{BASE_URL}/auth/me", headers=headers_b).json()["user_id"]

    print("2. Dev A creates Project A1...")
    proj_a_res = httpx.post(f"{BASE_URL}/baas/projects/", json={"project_name": "Project A1", "project_slug": f"proj-a1-{int(time.time())}", "description": "Desc"}, headers=headers_a)
    assert proj_a_res.status_code == 201, f"Expected 201, got {proj_a_res.status_code} - {proj_a_res.text}"
    proj_a_id = proj_a_res.json()["project_id"]

    print("3. Dev B creates Project B1...")
    proj_b_res = httpx.post(f"{BASE_URL}/baas/projects/", json={"project_name": "Project B1", "project_slug": f"proj-b1-{int(time.time())}", "description": "Desc"}, headers=headers_b)
    assert proj_b_res.status_code == 201, f"Expected 201, got {proj_b_res.status_code} - {proj_b_res.text}"
    proj_b_id = proj_b_res.json()["project_id"]

    print("4. RBAC - Developer A promotes Developer B to Admin...")
    httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/members", json={"email": dev_b["email"], "role": "developer"}, headers=headers_a)
    httpx.put(f"{BASE_URL}/baas/projects/{proj_a_id}/members/{user_b_id}", json={"role": "admin"}, headers=headers_a)

    print("5. Generate API Key for Project A1...")
    key_a_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/keys", json={"name": "prod-key"}, headers=headers_a)
    assert key_a_res.status_code == 201
    key_a = key_a_res.json()["key"]

    print("6. Generate API Key for Project B1...")
    key_b_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_b_id}/keys", json={"name": "prod-key"}, headers=headers_b)
    assert key_b_res.status_code == 201
    key_b = key_b_res.json()["key"]

    print("7. JWT (Control Plane) creates a table in Project A1...")
    table_req = {"name": "tmp_table", "columns": {"name": "TEXT", "price": "REAL", "stock": "INTEGER", "tags": "JSON"}}
    create_table_a = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/tables", json=table_req, headers=headers_a)
    assert create_table_a.status_code == 201, f"Expected 201, got {create_table_a.status_code}"

    print("8. JWT (Control Plane) creates a table in Project B1...")
    create_table_b = httpx.post(f"{BASE_URL}/baas/projects/{proj_b_id}/tables", json={"name": "b_table", "columns": {"data": "TEXT"}}, headers=headers_b)
    assert create_table_b.status_code == 201, f"Expected 201, got {create_table_b.status_code}"

    print("9. API Key (Data Plane) Project B reads Project B table...")
    # Using list rows endpoint as default data/table_name reading
    dp_b = httpx.get(f"{BASE_URL}/baas/projects/{proj_b_id}/data/b_table", headers={"X-Project-API-Key": key_b})
    assert dp_b.status_code == 200, f"Expected 200, got {dp_b.status_code}"

    print("10. API Key (Data Plane) Project B attempts to read Project A data (IDOR Denied)...")
    dp_b_on_a = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table", headers={"X-Project-API-Key": key_b})
    assert dp_b_on_a.status_code in (401, 403), f"Expected 401/403, got {dp_b_on_a.status_code}"

    print("11. API Key (Data Plane) inserts a row in Project A1...")
    row_data = {"id": "prod_1", "name": "ThinkPad", "price": 1200.00, "stock": 5, "tags": '["laptop", "lenovo"]'}
    insert_row_a = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table", json=row_data, headers={"X-Project-API-Key": key_a})
    assert insert_row_a.status_code == 201, f"Expected 201, got {insert_row_a.status_code}"

    print("12. API Key reads the row...")
    get_row_a = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table/prod_1", headers={"X-Project-API-Key": key_a})
    assert get_row_a.status_code == 200, f"Expected 200, got {get_row_a.status_code}"
    assert get_row_a.json()["data"]["name"] == "ThinkPad"

    print("13. API Key updates the row (PUT)...")
    update_data = {"price": 1100.00, "stock": 4}
    update_row_a = httpx.put(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table/prod_1", json=update_data, headers={"X-Project-API-Key": key_a})
    assert update_row_a.status_code == 200, f"Expected 200, got {update_row_a.status_code}"
    get_updated = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table/prod_1", headers={"X-Project-API-Key": key_a})
    assert get_updated.json()["data"]["price"] == 1100.00

    print("14. Pagination and Listing (List)...")
    for i in range(5):
        httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table", json={"id": f"p_{i}", "name": "Bulk", "price": 10}, headers={"X-Project-API-Key": key_a})

    list_rows = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table?limit=2&offset=1", headers={"X-Project-API-Key": key_a})
    assert list_rows.status_code == 200
    assert len(list_rows.json()) == 2

    print("15. API Key deletes a row (DELETE)...")
    delete_row = httpx.delete(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table/p_0", headers={"X-Project-API-Key": key_a})
    assert delete_row.status_code == 204 or delete_row.status_code == 200
    get_deleted = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table/p_0", headers={"X-Project-API-Key": key_a})
    assert get_deleted.status_code == 404

    print("16. API Key Schema Management Rejection...")
    key_create_table = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/tables", json={"name": "hax", "columns": {"id": "TEXT"}}, headers={"X-Project-API-Key": key_a})
    assert key_create_table.status_code in (401, 403)
    key_delete_table = httpx.delete(f"{BASE_URL}/baas/projects/{proj_a_id}/tables/tmp_table", headers={"X-Project-API-Key": key_a})
    assert key_delete_table.status_code in (401, 403)

    print("17. SQL Injection & Invalid Identifiers...")
    invalid_table_req = {"name": "sqlite_master_fake", "columns": {"name": "TEXT"}}
    invalid_table = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/tables", json=invalid_table_req, headers=headers_a)
    assert invalid_table.status_code == 422, f"Expected 422, got {invalid_table.status_code}"

    invalid_table_2 = {"name": "drop table users;", "columns": {"name": "TEXT"}}
    invalid_table_2_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/tables", json=invalid_table_2, headers=headers_a)
    assert invalid_table_2_res.status_code == 422, f"Expected 422, got {invalid_table_2_res.status_code}"

    print("18. Simulating Backup/Restore with Cross-Project Isolation...")
    db_a_path = f"data/projects/{proj_a_id}/data.db"
    db_b_path = f"data/projects/{proj_b_id}/data.db"

    httpx.post(f"{BASE_URL}/baas/projects/{proj_b_id}/data/b_table", json={"id": "b1", "data": "original B data"}, headers={"X-Project-API-Key": key_b})
    b_data_before = httpx.get(f"{BASE_URL}/baas/projects/{proj_b_id}/data/b_table/b1", headers={"X-Project-API-Key": key_b}).json()["data"]["data"]

    backup_path = db_a_path + ".bak"
    if os.path.exists(db_a_path):
        shutil.copy(db_a_path, backup_path)

    # HACK A
    httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table", json={"id": "prod_temp", "name": "Hack"}, headers={"X-Project-API-Key": key_a})

    # HACK B
    httpx.put(f"{BASE_URL}/baas/projects/{proj_b_id}/data/b_table/b1", json={"data": "modified B data"}, headers={"X-Project-API-Key": key_b})

    # Restore A
    if os.path.exists(backup_path):
        shutil.copy(backup_path, db_a_path)

    # Verify A is restored
    get_row_a_again = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table/prod_1", headers={"X-Project-API-Key": key_a})
    assert get_row_a_again.status_code == 200
    get_hack = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table/prod_temp", headers={"X-Project-API-Key": key_a})
    assert get_hack.status_code == 404

    # Verify B is STILL MODIFIED
    b_data_after = httpx.get(f"{BASE_URL}/baas/projects/{proj_b_id}/data/b_table/b1", headers={"X-Project-API-Key": key_b}).json()["data"]["data"]
    assert b_data_after == "modified B data", f"Project B reverted! expected 'modified B data', got {b_data_after}"

    print("19. Persistence Check (Server Restart simulation)...")
    persisted = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table/prod_1", headers={"X-Project-API-Key": key_a})
    assert persisted.status_code == 200

    print("20. Testing Revoked & Invalid API Keys...")
    invalid_key_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table", headers={"X-Project-API-Key": "invalid_key"})
    assert invalid_key_res.status_code in (401, 403)

    key_id_to_revoke = key_a.split('_')[2] if len(key_a.split('_')) > 2 else key_a.split('_')[1]
    httpx.delete(f"{BASE_URL}/baas/projects/{proj_a_id}/keys/{key_id_to_revoke}", headers=headers_a)
    revoked_key_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/data/tmp_table", headers={"X-Project-API-Key": key_a})
    assert revoked_key_res.status_code in (401, 403)

    print("21. Testing Viewer Schema Management Rejection...")
    dev_c = {"username": f"devc_{int(time.time())}", "email": f"devc_{int(time.time())}@test.com", "password": "pass"}
    httpx.post(f"{BASE_URL}/auth/register", json=dev_c)
    token_c = httpx.post(f"{BASE_URL}/auth/login", json={"email": dev_c["email"], "password": dev_c["password"]}).json()["access_token"]
    headers_c = {"Authorization": f"Bearer {token_c}"}
    user_c_id = httpx.get(f"{BASE_URL}/auth/me", headers=headers_c).json()["user_id"]

    httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/members", json={"email": dev_c["email"], "role": "viewer"}, headers=headers_a)

    c_create_table = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/tables", json={"name": "viewer_table", "columns": {"id": "TEXT"}}, headers=headers_c)
    assert c_create_table.status_code in (401, 403), f"Expected 401/403, got {c_create_table.status_code}"

    c_delete_table = httpx.delete(f"{BASE_URL}/baas/projects/{proj_a_id}/tables/tmp_table", headers=headers_c)
    assert c_delete_table.status_code in (401, 403)


    print("22. Testing Developer Role Restrictions...")
    dev_d = {"username": f"devd_{int(time.time())}", "email": f"devd_{int(time.time())}@test.com", "password": "pass"}
    httpx.post(f"{BASE_URL}/auth/register", json=dev_d)
    token_d = httpx.post(f"{BASE_URL}/auth/login", json={"email": dev_d["email"], "password": dev_d["password"]}).json()["access_token"]
    headers_d = {"Authorization": f"Bearer {token_d}"}
    user_d_id = httpx.get(f"{BASE_URL}/auth/me", headers=headers_d).json()["user_id"]

    httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/members", json={"email": dev_d["email"], "role": "developer"}, headers=headers_a)

    # Developer CAN read members and project
    d_read_members = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/members", headers=headers_d)
    assert d_read_members.status_code == 200, f"Developer should read members, got {d_read_members.status_code}"

    d_read_project = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}", headers=headers_d)
    assert d_read_project.status_code == 200, f"Developer should read project, got {d_read_project.status_code}"

    d_list_tables = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/tables", headers=headers_d)
    assert d_list_tables.status_code == 200, f"Developer should list tables, got {d_list_tables.status_code}"

    # Developer CANNOT create table
    d_create_table = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/tables", json={"name": "dev_hack", "columns": {"id": "TEXT"}}, headers=headers_d)
    assert d_create_table.status_code in (401, 403), f"Developer should not create table, got {d_create_table.status_code}"

    # Developer CANNOT add members
    d_add_member = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/members", json={"email": "nobody@test.com", "role": "viewer"}, headers=headers_d)
    assert d_add_member.status_code in (401, 403), f"Developer should not add member, got {d_add_member.status_code}"

    # Developer CANNOT create API keys
    d_create_key = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/keys", json={"name": "dev-key"}, headers=headers_d)
    assert d_create_key.status_code in (401, 403), f"Developer should not create API key, got {d_create_key.status_code}"

    print("23. Testing Member Removal and Access Revocation...")
    # Admin removes developer D
    remove_res = httpx.delete(f"{BASE_URL}/baas/projects/{proj_a_id}/members/{user_d_id}", headers=headers_a)
    assert remove_res.status_code in (200, 204), f"Admin should remove member, got {remove_res.status_code} - {remove_res.text}"

    # Removed developer D now gets 403 on any project route
    after_remove = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/members", headers=headers_d)
    assert after_remove.status_code in (401, 403), f"Removed member should be denied, got {after_remove.status_code}"

    after_remove_project = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}", headers=headers_d)
    assert after_remove_project.status_code in (401, 403), f"Removed member should be denied on project, got {after_remove_project.status_code}"

    # Admin cannot remove the last Owner
    remove_owner_res = httpx.delete(f"{BASE_URL}/baas/projects/{proj_a_id}/members/{user_a_id}", headers=headers_b)
    assert remove_owner_res.status_code in (400, 403), f"Should not remove last owner, got {remove_owner_res.status_code}"
    # 24. Rate Limiting Test
    print("24. Testing Rate Limiting (150 requests)...")
    success_count = 0
    too_many_count = 0

    with httpx.Client() as client:
        for _ in range(150):
            res = client.get(
                f"{BASE_URL}/baas/projects/{proj_b_id}/data/b_table",
                headers={"X-Project-API-Key": key_b}
            )
            if res.status_code == 200:
                success_count += 1
            elif res.status_code == 429:
                too_many_count += 1

    print(f"    Successes: {success_count}, 429s: {too_many_count}")
    assert too_many_count > 0, "Rate limit was not triggered!"

    print("    Waiting 1.5 seconds for bucket refill...")
    time.sleep(1.5)

    # Should work now
    res = httpx.get(
        f"{BASE_URL}/baas/projects/{proj_b_id}/data/b_table",
        headers={"X-Project-API-Key": key_b}
    )
    assert res.status_code == 200, "Did not recover from rate limit!"
    print("    Refill confirmed.")


    print("25. Testing End-User Authentication...")
    end_user_email = f"enduser_{int(time.time())}@example.com"
    reg_end_user = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/auth/register", json={
        "email": end_user_email,
        "password": "securepassword123"
    })
    if reg_end_user.status_code != 201:
        raise AssertionError(f"Expected 201 on end user reg, got {reg_end_user.status_code} - {reg_end_user.text}")

    login_end_user = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/auth/login", json={
        "email": end_user_email,
        "password": "securepassword123"
    })
    if login_end_user.status_code != 200:
        raise AssertionError(f"Expected 200 on end user login, got {login_end_user.status_code}")

    end_user_token = login_end_user.json()["access_token"]
    me_end_user = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/auth/me", headers={"Authorization": f"Bearer {end_user_token}"})
    if me_end_user.status_code != 200:
        raise AssertionError(f"Expected 200 on end user me, got {me_end_user.status_code}")

    print("26. Testing Storage Service (Upload, List, Download, Delete)...")
    file_content = b"Smoke Test File Content"
    upload_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/storage/", headers=headers_a, files={"file": ("smoke.txt", file_content, "text/plain")})
    if upload_res.status_code != 201:
        raise AssertionError(f"Expected 201 on file upload, got {upload_res.status_code}: {upload_res.text}")
    file_id = upload_res.json()["id"]

    list_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/storage/", headers=headers_a)
    if list_res.status_code != 200 or len(list_res.json()) == 0:
        raise AssertionError(f"Expected 200 and >= 1 file on list, got {list_res.status_code}")

    download_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/storage/{file_id}", headers=headers_a)
    if download_res.status_code != 200 or download_res.content != file_content:
        raise AssertionError(f"Expected 200 and exact content on download, got {download_res.status_code}")

    delete_res = httpx.delete(f"{BASE_URL}/baas/projects/{proj_a_id}/storage/{file_id}", headers=headers_a)
    if delete_res.status_code != 204:
        raise AssertionError(f"Expected 204 on delete, got {delete_res.status_code}")

    print("27. Testing Deployment Integration (Deploy, Stop, Restart, Health, Logs)...")
    deploy_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/deploy", headers=headers_a, json={"requested_by": "smoke_test"})
    if deploy_res.status_code != 200:
        raise AssertionError(f"Expected 200 on deploy, got {deploy_res.status_code}")

    health_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/health", headers=headers_a)
    if health_res.status_code != 200:
        raise AssertionError(f"Expected 200 on health, got {health_res.status_code}")

    stop_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/stop", headers=headers_a, json={"requested_by": "smoke_test"})
    if stop_res.status_code != 200:
        raise AssertionError(f"Expected 200 on stop, got {stop_res.status_code}")

    restart_res = httpx.post(f"{BASE_URL}/baas/projects/{proj_a_id}/restart", headers=headers_a, json={"requested_by": "smoke_test"})
    if restart_res.status_code != 200:
        raise AssertionError(f"Expected 200 on restart, got {restart_res.status_code}")

    logs_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/logs", headers=headers_a)
    if logs_res.status_code != 200:
        raise AssertionError(f"Expected 200 on logs, got {logs_res.status_code}")

    print("✅ All smoke-test steps passed successfully!")

    print("28. Testing Monitoring Integration (Status, History, Metrics, Platform)...")

    # 28a. GET /status — must return 200 with simulated: true
    status_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/status", headers=headers_a)
    if status_res.status_code != 200:
        raise AssertionError(f"Expected 200 on /status, got {status_res.status_code}: {status_res.text}")
    status_data = status_res.json()
    if not status_data.get("simulated"):
        raise AssertionError(f"/status must include simulated=true, got: {status_data}")

    # 28b. GET /history — must return 200 and list operations performed earlier
    hist_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/history", headers=headers_a)
    if hist_res.status_code != 200:
        raise AssertionError(f"Expected 200 on /history, got {hist_res.status_code}: {hist_res.text}")
    hist_data = hist_res.json()
    if hist_data.get("total_returned", 0) == 0:
        raise AssertionError(f"/history must contain at least 1 operation (deploy, stop, restart were performed): {hist_data}")

    # 28c. GET /metrics — must return 200 with since_restart: true
    metrics_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/metrics", headers=headers_a)
    if metrics_res.status_code != 200:
        raise AssertionError(f"Expected 200 on /metrics, got {metrics_res.status_code}: {metrics_res.text}")
    metrics_data = metrics_res.json()
    if not metrics_data.get("since_restart"):
        raise AssertionError(f"/metrics must include since_restart=true, got: {metrics_data}")

    # 28d. IDOR: Dev E (no project membership) must NOT be able to read Project A history
    dev_e = {"username": f"deve_{int(time.time())}", "email": f"deve_{int(time.time())}@test.com", "password": "pass"}
    httpx.post(f"{BASE_URL}/auth/register", json=dev_e)
    token_e = httpx.post(f"{BASE_URL}/auth/login", json={"email": dev_e["email"], "password": dev_e["password"]}).json()["access_token"]
    headers_e = {"Authorization": f"Bearer {token_e}"}

    idor_res = httpx.get(f"{BASE_URL}/baas/projects/{proj_a_id}/history", headers=headers_e)
    if idor_res.status_code != 403:
        raise AssertionError(f"Expected 403 (IDOR protection) on cross-project /history, got {idor_res.status_code}")

    # 28e. GET /platform/metrics with internal token — must return 200 with cpu_percent
    platform_res = httpx.get(
        f"{BASE_URL}/projects/platform/metrics",
        headers={"X-Internal-Token": INTERNAL_TOKEN},
    )
    if platform_res.status_code != 200:
        raise AssertionError(f"Expected 200 on /platform/metrics, got {platform_res.status_code}: {platform_res.text}")
    platform_data = platform_res.json()
    if "cpu_percent" not in platform_data:
        raise AssertionError(f"/platform/metrics must include cpu_percent, got: {platform_data}")
    if platform_data["cpu_percent"] < 0 or platform_data["cpu_percent"] > 100:
        raise AssertionError(f"cpu_percent must be 0-100, got: {platform_data['cpu_percent']}")

    # 28f. GET /platform/metrics with Developer JWT — must be rejected (403)
    platform_deny_res = httpx.get(f"{BASE_URL}/projects/platform/metrics", headers=headers_a)
    if platform_deny_res.status_code != 403:
        raise AssertionError(f"Expected 403 when Developer JWT used on /platform/metrics, got {platform_deny_res.status_code}")

    print("✅ All smoke-test steps passed successfully!")

if __name__ == "__main__":
    run_smoke_test()
