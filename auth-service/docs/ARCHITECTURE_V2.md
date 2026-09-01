# Architecture V2: Validated Platform Orchestrator

This document represents the **current validated architecture** of the Platform Orchestrator following the Phase 23 lock.

*(Note: `ARCHITECTURE_V1.md` remains in this directory purely as a historical artifact. Its claims regarding a "Phase 11" migration to PostgreSQL, Redis, Kubernetes, and S3 were explicitly abandoned in favor of the architecture described below).*

## 1. Core Principles
The platform remains firmly rooted in the Phase 9A Engine/Adapter/Coordinator model:
- **Engines** own operational workflows (Backup, Restore, Deployment, Health, Lifecycle).
- **The Coordinator** owns internal dispatching and API-to-Engine translation.
- **Adapters** own the storage/infrastructure boundaries.

## 2. The Current Validated Persistence Layer
Rather than migrating to heavy infrastructure, the platform uses a strictly verified, isolated persistence model:
- **Database:** SQLite. The platform provisions a distinct, isolated SQLite database file per project/tenant (`/var/lib/auth-service/data/{project_id}/{project_id}.sqlite3`).
- **Storage:** Local File Storage. The platform uses local disk directories, isolating project blobs to `/var/lib/auth-service/data/{project_id}/`.
- PostgreSQL integration (`database.py`) was entirely deleted from the repository.

## 3. The Verified Orchestration Boundary
- **Deployment:** The platform simulates container deployment states via `DockerDeploymentProvider`. It does not physically connect to the Docker socket to spin up containers.
- **Backups:** The `BackupEngine` currently implements backup operation/manifest metadata orchestration. Physical byte-level backup of tenant SQLite/blob data is currently simulated.
- **Restores:** The `RestoreEngine` currently implements restore operation/manifest lifecycle orchestration. Physical byte-level restoration of tenant SQLite/blob data is currently simulated.
- **Health:** The `HealthEngine` continuously monitors SQLite latency (must be <500ms) and host disk availability passively.

## 4. The API and Security Layer
- **Ingress:** FastAPI forms the single public entry point.
- **Identity:** All authentication is secured via PyJWT utilizing the `HS256` symmetric algorithm. The application explicitly enforces this algorithm and ignores asymmetric/elliptic-curve cryptography.
- **Middleware:** Security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`) are enforced globally at the application level. HSTS is delegated to edge TLS termination.
