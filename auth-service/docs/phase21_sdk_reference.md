# Phase 21 SDK Reference

This document serves as the durable reference for the `homelab_sdk` created in Phase 21.

## Architecture & Boundary
The Python SDK acts as the exclusive programmatic boundary for external applications interacting with the Homelab platform. It exposes no direct access to PostgreSQL, MinIO, or internal orchestrators. All communication occurs purely over HTTP targeting the public API ingress (`/api/v1/baas/*` and `/api/v1/auth/*`).

## Dual-Plane Authentication Mappings
The SDK accurately respects the established platform authentication planes:

1. **Management Plane**
   - **Credential**: Developer Bearer Token (`access_token`)
   - **Operations**: `client.admin`, `client.projects`, `client.teammates`, `client.apikeys`, `client.schema`
   - **Use Case**: Infrastructure provisioning, teammate management, API key generation.

2. **Data / Storage Plane**
   - **Credential**: Project API Key (`X-Project-API-Key`)
   - **Operations**: `client.db` (insert, list, read, update, delete), `client.storage` (upload, list, download, delete)
   - **Use Case**: Row manipulation and attachment storage by external applications on behalf of the project.

3. **End-User Plane**
   - **Credential**: End-User Bearer Token
   - **Operations**: `client.auth` (login, register, `/me`)
   - **Use Case**: Identity management strictly isolated to the project's user pool.

## Operation History & Status Verification
Asynchronous operations (e.g., Backup, Restore, Deploy) return an `OperationResponse` containing an `operation_id`.

The SDK provides `client.projects.history(project_id)` to poll and retrieve the terminal state of these operations. Status monitoring is exposed via `client.projects.status(project_id)`.
