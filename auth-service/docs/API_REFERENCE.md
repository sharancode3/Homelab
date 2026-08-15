# Homelab BaaS: API Reference

This document covers the currently implemented and verified HTTP endpoints.

## Base URL
All API paths are prefixed with `/api/v1`.

---

## 1. Authentication Endpoints (`/auth/*`)
All endpoints utilize JWT tokens (`HS256` symmetric algorithm).

### `POST /auth/register`
Creates a new developer account.
- **Body:** `{ "email": "str", "username": "str", "password": "str" }`
- **Response:** `200 OK` + User Object

### `POST /auth/login`
Authenticates a user and returns an `access_token` (Developer Bearer Token).
- **Body:** `OAuth2PasswordRequestForm` (username, password)
- **Response:** `200 OK` + `{ "access_token": "...", "token_type": "bearer" }`

### `POST /auth/end-users/register`
Registers an end-user isolated to a specific project pool.
- **Headers:** `X-Project-API-Key: <Project API Key>`
- **Body:** `{ "email": "str", "password": "str" }`
- **Response:** `200 OK`

### `POST /auth/end-users/login`
Authenticates an end-user.
- **Headers:** `X-Project-API-Key: <Project API Key>`
- **Body:** `OAuth2PasswordRequestForm`
- **Response:** `200 OK` + `{ "access_token": "...", "token_type": "bearer" }`

---

## 2. Infrastructure Endpoints (`/baas/projects/*`)
Secured by **Developer Bearer Token**.

### `POST /baas/projects`
Provisions a new project with a dedicated SQLite database and Storage path.
- **Body:** `{ "project_name": "str" }`
- **Response:** `200 OK` + `{ "project_id": "...", "project_name": "..." }`

### `POST /baas/projects/{project_id}/apikeys`
Generates a persistent API key for SDK/external app access.
- **Body:** `{ "name": "str", "key_type": "live|test" }`
- **Response:** `200 OK` + `{ "key": "pk_live_..." }`

### `POST /baas/projects/{project_id}/deploy` / `pause` / `resume`
Triggers simulated orchestration workflows against the internal state machine.
- **Response:** `202 Accepted` + `{ "operation_id": "..." }`

### `POST /baas/projects/{project_id}/backup`
Creates a point-in-time snapshot of the SQLite database and storage blobs.
- **Response:** `202 Accepted` + `{ "operation_id": "..." }`
- *Note: To perform a Restore, you must retrieve the `backup_id` from the Operation status after the Backup completes.*

### `POST /baas/projects/{project_id}/restore`
Reverts the project state to a specific `backup_id`.
- **Body:** `{ "backup_id": "str" }`
- **Response:** `202 Accepted` + `{ "operation_id": "..." }`

---

## 3. Data & Storage Endpoints (`/baas/db/*` & `/baas/storage/*`)
Secured by **Project API Key**.

### `POST /baas/db/rows`
Inserts a record into the project's SQLite DB.
- **Body:** `{ "table_name": "str", "data": { ... } }`
- **Response:** `200 OK` + `{ "id": "..." }`

### `POST /baas/storage/upload`
Uploads a file to local storage. (Max 5MB).
- **Form-Data:** `file` (UploadFile)
- **Response:** `200 OK` + `{ "file_id": "..." }`

---

## 4. Platform Health
### `GET /health/platform`
Observational endpoint exposing real-time system and disk health state.
- **Response:** `200 OK` (Healthy/Degraded) or `503 Service Unavailable` (Unhealthy). Includes SQLite latency metrics and Disk Space free capacity (MB).
