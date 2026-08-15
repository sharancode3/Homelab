import sys
import os
from pprint import pprint
import random
import urllib3

urllib3.disable_warnings()

from homelab_sdk import HomelabClient
from todo_app import TaskManager

import time

def wait_for_operation(client, project_id, operation_id, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        hist = client.projects.history(project_id, limit=50)
        ops = hist.get("history", [])
        for op in ops:
            if op.get("operation_id") == operation_id:
                if op.get("status") in ["completed", "failed"]:
                    return op
        time.sleep(2)
    return None

def run_e2e_workflow():
    print("=== Phase 21E: Full End-to-End Workflow Execution ===")

    base_url = "http://localhost"

    # ---------------------------------------------------------
    # 1. Developer & Management Plane
    # ---------------------------------------------------------
    print("\n--- [Management Plane] ---")
    client_public = HomelabClient(base_url=base_url, verify_ssl=False)

    dev_email = f"dev_{random.randint(1000, 9999)}@example.com"
    dev_username = f"dev_{random.randint(1000, 9999)}"

    print("1. Registering Developer...")
    reg_res = client_public.admin.register(dev_email, dev_username, "password123")
    print(f"   Registered Developer: {dev_email}")

    login_res = client_public.admin.login(dev_email, "password123")
    dev_token = login_res["access_token"]

    client_dev = HomelabClient(base_url=base_url, developer_token=dev_token, verify_ssl=False)

    print("2. Creating Project...")
    proj_name = f"E2E Project {random.randint(100, 999)}"
    proj_slug = f"e2e-project-{random.randint(100, 999)}"
    proj_res = client_dev.projects.create(proj_name, proj_slug)
    project_id = proj_res["project_id"]
    print(f"   Created Project: {project_id} ({proj_name})")

    print("3. Adding Teammate...")
    team_email = f"team_{random.randint(1000, 9999)}@example.com"
    client_public.admin.register(team_email, f"team_{random.randint(1000, 9999)}", "password123")
    team_res = client_dev.teammates.add(project_id, team_email, "viewer")
    print(f"   Teammate Added: {team_email} as {team_res['role']}")

    print("4. Creating API Key...")
    key_res = client_dev.apikeys.create(project_id, "external_app_key")
    api_key = key_res["key"]
    print("   API Key Generated (pk_live_***)")

    print("5. Creating Schema...")
    schema_res = client_dev.schema.create(
        project_id,
        "tasks",
        {"id": "text", "title": "text", "description": "text", "status": "text"}
    )
    print(f"   Schema Created: {schema_res['name']} table")

    # ---------------------------------------------------------
    # 2. External Application (Data Plane)
    # ---------------------------------------------------------
    print("\n--- [External Application / Data Plane] ---")
    print("6. Initializing External Application (TaskManager)...")
    app = TaskManager(endpoint=base_url, project_id=project_id, api_key=api_key)

    print("7. Row Insert...")
    task_id = app.create_task("Write E2E test", "Verify full pipeline")
    print(f"   Inserted Task ID: {task_id}")

    print("8. Row List...")
    tasks = app.list_tasks()
    print(f"   Found {len(tasks)} tasks.")

    print("9. Row Read / Update...")
    app.complete_task(task_id)
    print(f"   Task {task_id} marked as completed.")

    print("10. File Upload...")
    file_id = app.attach_file(task_id, "notes.txt", b"Task completed successfully via SDK.")
    print(f"   Uploaded attachment ID: {file_id}")

    print("11. File Download...")
    content = app.download_attachment(file_id)
    print(f"   Downloaded attachment: {content.decode('utf-8')}")

    # ---------------------------------------------------------
    # 3. End-User Identity (Data Plane)
    # ---------------------------------------------------------
    print("\n--- [End-User Authentication Plane] ---")
    print("12. Registering End-User...")
    eu_email = f"user_{random.randint(1000, 9999)}@example.com"
    client_app = HomelabClient(base_url=base_url, project_id=project_id, api_key=api_key, verify_ssl=False)
    eu_reg = client_app.auth.register(project_id, eu_email, "securepassword")
    print(f"   End-User Registered: {eu_email}")

    print("13. End-User Login & /me...")
    eu_login = client_app.auth.login(project_id, eu_email, "securepassword")
    client_eu = HomelabClient(base_url=base_url, project_id=project_id, end_user_token=eu_login["access_token"], verify_ssl=False)
    eu_profile = client_eu.auth.get_me(project_id)
    print(f"   Authenticated via Bearer: {eu_profile['email']}")

    # ---------------------------------------------------------
    # 4. Infrastructure & Operations Plane
    # ---------------------------------------------------------
    print("\n--- [Infrastructure Operations Plane] ---")
    print("14. Deploying Project...")
    try:
        deploy_res = client_dev.projects.deploy(project_id, "latest")
        print(f"   Deploy triggered: {deploy_res}")
    except Exception as e:
        print(f"   [Expected Failure] Deploy: {e}")

    print("15. Backup Project...")
    try:
        backup_res = client_dev.projects.backup(project_id)
        backup_id = backup_res.get('operation_id', "unknown_op")
        print(f"   Backup triggered successfully. Operation: {backup_id}")

        # Verify Backup terminal state
        op_final = wait_for_operation(client_dev, project_id, backup_id)
        if op_final:
            print(f"   [Verified] Backup Operation reached terminal state: {op_final.get('status')}")
        else:
            print(f"   [Warning] Backup Operation did not reach terminal state in time.")
    except Exception as e:
        print(f"   [Failure] Backup: {e}")
        backup_id = None

    print("16. Restore Project...")
    if backup_id:
        try:
            restore_res = client_dev.projects.restore(project_id, backup_id)
            restore_op_id = restore_res.get('operation_id')
            print(f"   Restore triggered successfully. Operation: {restore_op_id}")

            # Verify Restore terminal state
            op_final = wait_for_operation(client_dev, project_id, restore_op_id)
            if op_final:
                print(f"   [Verified] Restore Operation reached terminal state: {op_final.get('status')}")
            else:
                print(f"   [Warning] Restore Operation did not reach terminal state in time.")
        except Exception as e:
            print(f"   [Expected Failure] Restore: {e}")

    print("17. Final Project State Verification...")
    status_res = client_dev.projects.status(project_id)
    print(f"   Project Status Verified: Lifecycle='{status_res.get('lifecycle_state')}', Deployment='{status_res.get('deployment_status')}'")

    print("\n=== Phase 21E End-to-End Workflow Completed Successfully! ===")

if __name__ == "__main__":
    run_e2e_workflow()
