# Homelab Backend-as-a-Service (BaaS)

Welcome to the Homelab BaaS repository. This repository contains the complete implementation of a secure, multi-tenant developer platform, providing Authentication, Database, Storage, and Deployment capabilities.

## Repository Structure

- **`auth-service/`**: The core Platform Orchestrator (FastAPI, Python). Manages tenants, authentication, projects, and the internal operations lifecycle.
- **`sdk-python/`**: The `homelab_sdk` Python client for interacting with the public API.
- **`external-app/`**: A verified end-to-end task management application that relies on the Platform Orchestrator and SDK.

## Documentation

The primary operational and developer documentation is located in `auth-service/docs/`:

1. **[Developer Guide](auth-service/docs/DEVELOPER_GUIDE.md)**: The end-to-end journey for creating an account, provisioning a project, and using the SDK.
2. **[API Reference](auth-service/docs/API_REFERENCE.md)**: Details on the `/api/v1/baas/*` and `/api/v1/auth/*` endpoints.
3. **[Security & Limits](auth-service/docs/SECURITY_AND_LIMITS.md)**: Cryptographic guarantees, RBAC boundaries, and resource limits.
4. **[Deployment Guide](auth-service/docs/DEPLOYMENT.md)**: Docker configuration and production deployment requirements.
5. **[Architecture](auth-service/docs/ARCHITECTURE_V2.md)**: The current validated platform architecture and engine design.

## Phase Execution History

This project follows a strict 25-Phase roadmap. Execution records and historical locks are strictly maintained. Do not modify historical architecture documents (e.g., `ARCHITECTURE_V1.md`) or verification artifacts. All current operational claims must be evaluated against the active implementation.
