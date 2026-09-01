# Homelab BaaS: Security & Limits

This document details the verified security boundaries and resource constraints currently implemented in the platform.

## 1. Authentication Boundaries
The platform enforces three strictly isolated authentication planes:
1. **Management Plane**: Uses Developer Bearer Tokens. Secures infrastructure operations (creating projects, teammates, API keys).
2. **Data / Storage Plane**: Uses Project API Keys (`X-Project-API-Key`). Secures SDK interactions (DB reads/writes, blob storage) explicitly bound to a single project footprint.
3. **End-User Plane**: Uses End-User Bearer Tokens. Identity operations strictly isolated within the boundaries of a specific project ID.

## 2. Cryptographic Implementation
- **JWT Standard:** All tokens are generated and verified exclusively using `PyJWT`.
- **Algorithm:** The platform rigidly enforces the `HS256` (HMAC-SHA256) symmetric algorithm.
- **Secret Management:** Signatures are keyed with the `PLATFORM_SECRET_KEY` environment variable. The platform does NOT utilize elliptic curve cryptography (ECDSA/ES256) or asymmetric keys.

## 3. Resource & Storage Limits
The following limits are actively enforced by the platform's code:
- **Maximum File Upload Size:** 5 MB (`storage_max_file_size_bytes`). Files exceeding this limit are rejected by the Storage API.
- **Maximum Project Storage Quota:** 100 MB (`storage_max_project_quota_bytes`). Total combined blob storage for a single project cannot exceed this limit.

## 4. Host Disk-Health Thresholds
The `HealthEngine` continuously monitors host disk space for the volume mapped to `/var/lib/auth-service/data`.
- **Warning Threshold (< 500MB free):** The `/api/v1/health/platform` endpoint reports `DEGRADED`.
- **Critical Threshold (< 100MB free):** The `/api/v1/health/platform` endpoint reports `UNHEALTHY`.
*(Note: These are observational health indicators. The system does not currently automatically halt database transactions based on this metric).*

## 5. Deployment Constraints
- **Docker Memory Limit:** The `platform-orchestrator` container is strictly constrained to a maximum of `256M` of RAM in `docker-compose.yml` to prevent host resource starvation.
- **HTTP Security Headers:** The FastAPI application globally injects `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` on all responses. (HSTS is explicitly delegated to the edge TLS layer and is not injected by the application code).
