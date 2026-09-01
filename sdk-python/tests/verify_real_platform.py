import sys
import os
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from homelab_sdk import HomelabClient

def run_verification():
    print("--- Phase 21C SDK Verification ---")

    base_url = "http://localhost" # Real platform

    # 1. Developer Account Creation
    print("\n[1] Registering Developer Account...")
    client_public = HomelabClient(base_url=base_url, verify_ssl=False)

    import random
    dev_email = f"dev_{random.randint(1000, 9999)}@example.com"
    dev_username = f"dev_{random.randint(1000, 9999)}"

    reg_res = client_public.admin.register(dev_email, dev_username, "password123")
    print(f"Registered: {reg_res}")

    print("\n[2] Logging in Developer...")
    login_res = client_public.admin.login(dev_email, "password123")
    dev_token = login_res["access_token"]
    print("Login successful, obtained developer token.")

    # Instantiate Management Client
    client_dev = HomelabClient(base_url=base_url, developer_token=dev_token, verify_ssl=False)

    # 2. Project Creation
    print("\n[3] Creating Project...")
    proj_name = f"Test Project {random.randint(100, 999)}"
    proj_slug = f"test-project-{random.randint(100, 999)}"
    proj_res = client_dev.projects.create(proj_name, proj_slug)
    project_id = proj_res["project_id"]
    print(f"Created Project ID: {project_id}")

    # 3. Teammates
    print("\n[4] Adding Teammate...")
    team_email = f"team_{random.randint(1000, 9999)}@example.com"
    team_username = f"team_{random.randint(1000, 9999)}"
    client_public.admin.register(team_email, team_username, "password123")
    team_res = client_dev.teammates.add(project_id, team_email, "viewer")
    print(f"Added Teammate: {team_res}")

    # 4. API Keys
    print("\n[5] Creating API Key...")
    key_res = client_dev.apikeys.create(project_id, "test_key")
    api_key = key_res["key"]
    print(f"Created API Key: pk_live_***")

    # 5. Schema Creation
    print("\n[6] Creating Schema...")
    schema_res = client_dev.schema.create(
        project_id,
        "users",
        {"id": "text", "name": "text", "age": "integer"}
    )
    print(f"Created Schema: {schema_res}")

    # 6. Data Plane: Database Row CRUD
    print("\n[7] Database Row Operations...")
    client_app = HomelabClient(base_url=base_url, project_id=project_id, api_key=api_key, verify_ssl=False)

    row_id = f"user_{random.randint(1000, 9999)}"
    insert_res = client_app.db.insert(project_id, "users", {"id": row_id, "name": "Alice", "age": 30})
    print(f"Inserted row ID: {row_id}")

    list_res = client_app.db.list(project_id, "users")
    print(f"List rows: {list_res}")

    get_res = client_app.db.get(project_id, "users", row_id)
    print(f"Get row: {get_res}")

    client_app.db.update(project_id, "users", row_id, {"name": "Alice Updated", "age": 31})
    print("Updated row.")

    # 7. Data Plane: Storage
    print("\n[8] Storage Operations...")
    file_content = b"Hello world from SDK!"
    upload_res = client_app.storage.upload(project_id, "hello.txt", file_content, "text/plain")
    file_id = upload_res["id"]
    print(f"Uploaded file ID: {file_id}")

    files = client_app.storage.list(project_id)
    print(f"Listed files: {[f['filename'] for f in files]}")

    downloaded = client_app.storage.download(project_id, file_id)
    print(f"Downloaded content: {downloaded.decode('utf-8')}")

    client_app.storage.delete(project_id, file_id)
    print("Deleted file.")

    # 8. Data Plane: End-User Auth
    print("\n[9] End-User Identity Operations...")
    eu_email = f"user_{random.randint(1000, 9999)}@example.com"

    eu_reg = client_app.auth.register(project_id, eu_email, "securepass", {"role": "customer"})
    print(f"End-user registered: {eu_reg}")

    eu_login = client_app.auth.login(project_id, eu_email, "securepass")
    eu_token = eu_login["access_token"]
    print("End-user login successful.")

    client_eu = HomelabClient(base_url=base_url, project_id=project_id, end_user_token=eu_token, verify_ssl=False)
    eu_me = client_eu.auth.get_me(project_id)
    print(f"Authenticated End-User profile: {eu_me['email']}")

    # 9. Operations (Health/Deploy/Backup)
    print("\n[10] Infrastructure Operations...")
    health = client_dev.projects.get_health(project_id)
    print(f"Health: {health}")

    try:
        backup = client_dev.projects.backup(project_id)
        print(f"Backup triggered: {backup}")
    except Exception as e:
        print(f"Backup failed (may not be supported yet): {e}")

    try:
        deploy = client_dev.projects.deploy(project_id, "latest")
        print(f"Deploy triggered: {deploy}")
    except Exception as e:
        print(f"Deploy failed: {e}")

    print("\n--- SDK Verification Complete ---")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    run_verification()
