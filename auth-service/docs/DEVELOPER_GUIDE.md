# Homelab BaaS: Developer Guide

This guide details the complete, verified external-application workflow for utilizing the Homelab BaaS platform. All steps below represent verified operational behavior.

## 1. Getting Started: Developer Account Creation
First, you must register as a developer to gain access to the Management Plane.

**Endpoint:** `POST /api/v1/auth/register`
```json
{
  "email": "dev@example.com",
  "username": "dev",
  "password": "<YOUR_PASSWORD>"
}
```

**Login:** `POST /api/v1/auth/login`
You will receive an `access_token` (Developer Bearer Token). Include this in the `Authorization: Bearer <token>` header for all Management Plane API calls.

## 2. Provisioning Infrastructure
With your Developer Token, create an isolated project.

**Endpoint:** `POST /api/v1/baas/projects`
```json
{
  "project_name": "My External App"
}
```
*Note the `project_id` returned in the response.*

## 3. Generate an API Key
To allow your application to interact with the Data Plane, you must generate a Project API Key.

**Endpoint:** `POST /api/v1/baas/projects/{project_id}/apikeys`
```json
{
  "name": "Live Server Key",
  "key_type": "live"
}
```
*Save the returned API key (`pk_live_...`). This key grants data-plane access and cannot be retrieved again.*

## 4. Install the SDK
Your external application interacts with the platform securely via the Python SDK.

```bash
cd sdk-python
pip install -e .
```

## 5. Connect Application & Manage Data
Initialize the SDK using your API Key and Project ID.

```python
from homelab_sdk.client import HomelabClient

client = HomelabClient(
    base_url="http://localhost:8000",
    project_id="<YOUR_PROJECT_ID>",
    api_key="<YOUR_API_KEY>"
)

# Insert a record into the project's isolated SQLite database
client.db.insert("tasks", {"task": "Write documentation", "status": "done"})

# Upload a file to the project's local blob storage
file_id = client.storage.upload(file_path="report.pdf")
```

## 6. End-User Authentication
If your application manages end-users, the platform provides a completely isolated end-user identity pool for your project. Your application delegates registration and login to the platform's `/api/v1/auth/*` endpoints by injecting the `X-Project-API-Key` header.
