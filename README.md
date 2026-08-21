<p align="center">
  <strong>Your own Backend-as-a-Service — built from scratch, running on a ThinkPad.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Caddy-2-1F88C0?style=flat-square&logo=caddy&logoColor=white" />
  <img src="https://img.shields.io/badge/MinIO-S3--Compatible-C72E49?style=flat-square&logo=minio&logoColor=white" />
  <img src="https://img.shields.io/badge/Phase-15%20Locked-6C63FF?style=flat-square" />
  <img src="https://img.shields.io/badge/Status-Active%20Development-A855F7?style=flat-square" />
</p>

# Homelab

**Homelab** is a fully self-hosted, multi-tenant **Backend-as-a-Service (BaaS)** platform — think Supabase or Firebase, but running on hardware *you own*, with zero vendor lock-in and no monthly cloud bill.

It gives developers a complete backend in seconds:

- 🔐 **Authentication** — User sign-up, login, sessions, email verification, password reset
- 🗄️ **Database** — Per-project isolated databases with a full REST Data API
- 📦 **File Storage** — Project-scoped object storage with upload/download/delete
- 🚀 **Deployment** — Deploy, stop, restart, and health-check your apps via the platform API
- 🔑 **API Keys** — Generate scoped `pk_live_xxx` keys for external applications
- 👥 **Team Collaboration** — Multi-member projects with role-based access control (RBAC)
- 📊 **Monitoring** — Real-time CPU, RAM, container, and deployment status visibility
- 🔒 **Security-first** — Argon2id password hashing, JWT sessions, rate limiting, tenant isolation at every layer

Built and battle-tested on a **4 GB RAM ThinkPad**, proving that serious infrastructure does not require serious cloud spend.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Concepts](#core-concepts)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [API Surface](#api-surface)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Security Model](#security-model)
- [Build Philosophy](#build-philosophy)
- [Current Status and Roadmap](#current-status-and-roadmap)
- [Future Scope](#future-scope)
- [Contributing](#contributing)
- [License](#license)

---

## Architecture Overview

Homelab is built on a strict **layered orchestration model**. There are no god classes, no spaghetti dependencies, no shortcuts.

```
                         ┌─────────────────────────────────────┐
                         │          Internet / Clients          │
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                         │        Caddy Reverse Proxy           │
                         │    (TLS termination + routing)       │
                         └──────────────────┬──────────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                         │         FastAPI API Layer            │
                         │  /api/v1/auth  /api/v1/baas/...      │
                         └──────┬──────────────────┬───────────┘
                                │                  │
               ┌────────────────▼──┐    ┌──────────▼──────────────────┐
               │   Auth Service    │    │     BaaS Product Layer       │
               │  (Platform Users) │    │  Projects · DB · Storage     │
               │  JWT · Argon2id   │    │  API Keys · Auth · Deploy    │
               └────────────────┬──┘    └──────────┬──────────────────┘
                                │                  │
                         ┌──────▼──────────────────▼──────────┐
                         │    Platform Operations Coordinator   │
                         │        (Central Dispatcher)          │
                         └──┬──────┬──────┬──────┬──────┬──────┘
                            │      │      │      │      │
            ┌───────────────▼┐  ┌──▼───┐ ┌▼────┐ ┌▼────┐ ┌▼──────────────┐
            │   Lifecycle    │  │Valid.│ │Deploy│ │Backup│ │Health / Audit │
            │   Manager      │  │Engine│ │Engine│ │Engine│ │   / Events    │
            └────────────────┘  └──────┘ └──┬───┘ └──────┘ └───────────────┘
                                            │
                         ┌──────────────────▼──────────────────┐
                         │         Adapter / Provider Layer      │
                         │   DockerDeploymentProvider            │
                         │   LocalStorageProvider                │
                         │   SQLiteTenantConnectionFactory       │
                         └──────────────────┬──────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
          ┌─────────▼────────┐  ┌───────────▼──────┐  ┌────────────▼─────┐
          │  SQLite (system) │  │  Per-Tenant DBs   │  │  Local / MinIO   │
          │  users · audit   │  │  (per project)    │  │    Storage       │
          │  history · keys  │  │  full isolation   │  │                  │
          └──────────────────┘  └──────────────────┘  └──────────────────┘
```

### The Two-Brain Model

The platform separates concerns into two clear halves:

| Layer | Purpose |
|---|---|
| **Phase 9A — The Brain** | Internal workflow engines: Lifecycle, Validation, Deployment, Backup, Restore, Health, Events, Audit |
| **Phase 10 — The Body** | External shell: FastAPI, CORS, Docker, storage adapters, observability, reliability |

The Brain never touches HTTP. The Body never contains business logic. They communicate through strictly typed DTOs.

---

## Core Concepts

### 1. Engine Architecture — No God Classes

Every workflow engine owns exactly one domain and nothing more:

| Engine | Responsibility |
|---|---|
| `LifecycleManager` | State machine — valid transitions for a project (CREATED → DEPLOYED → STOPPED → …) |
| `ValidationEngine` | Read-only pre-flight checks before any operation executes |
| `DeploymentEngine` | Orchestrates deploy / pause / resume / rollback workflows |
| `BackupEngine` | Safely captures system state; generates immutable manifests |
| `RestoreEngine` | Validates integrity and reverts the system to a previous backup |
| `HealthEngine` | Passive, read-only health aggregation — never causes side effects |
| `EventEngine` | Deterministic publish / route / record for loose coupling |
| `AuditEngine` | Append-only, tamper-evident history of every platform operation |
| `PlatformOperationsCoordinator` | The central dispatcher — translates "Deploy Project X" into the correct engine sequence |

### 2. Adapter Pattern — Infrastructure Independence

Engines never import infrastructure directly. They depend on interfaces:

```
DeploymentEngine  →  DeploymentAdapter  (interface)
                              ↑
                  DockerDeploymentProvider  (real Docker API)
                  SimulatedDeploymentProvider  (test / dev)
```

Swapping Docker for Kubernetes is a one-provider swap — zero engine changes required.

### 3. Multi-Tenant Isolation

Every project is a hard, enforced isolation boundary. The authorization chain is:

```
Identity → Project membership → Permission → Resource → Operation
```

No layer may skip this chain. Project A's database, storage, users, and API keys are physically and logically inaccessible to Project B — enforced at the `SQLiteTenantConnectionFactory` level, not just at the application layer.

### 4. Authorization Chain (RBAC)

Every API request answers four questions in order:

```
Who?  →  Which project?  →  Which resource?  →  Which operation?  →  Allowed?
```

RBAC roles — `OWNER`, `ADMIN`, `DEVELOPER`, `VIEWER` — are enforced server-side on every request. Frontend UI hiding is never used as a security control.

### 5. Repository Pattern

Engines deal only with pure domain objects. All persistence is abstracted:

```
Engine  →  Repository  (interface)
                 ↑
         SQLiteXxxRepository  (current implementation)
         PostgreSQLXxxRepository  (roadmap)
```

When PostgreSQL replaces SQLite, only the repository implementation changes. The engines are untouched.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Runtime** | Python 3.11 | Application language |
| **Web Framework** | FastAPI + Uvicorn | Async REST API with OpenAPI docs |
| **Auth** | passlib[argon2] + python-jose | Argon2id password hashing + JWT tokens |
| **Database (system)** | SQLite | Platform metadata, audit log, user store |
| **Database (tenant)** | SQLite per project → PostgreSQL (roadmap) | Per-project data isolation |
| **Object Storage** | Local filesystem → MinIO (roadmap) | File upload / download / delete |
| **Reverse Proxy** | Caddy 2 | TLS termination, routing, automatic HTTPS |
| **Container Runtime** | Docker + Docker Compose | Service orchestration |
| **Data Validation** | Pydantic v2 + pydantic-settings | Request / response models, env config |
| **Rate Limiting** | In-process sliding window | Protection on auth, reset, and data endpoints |
| **Observability** | Structured logger via contextvars | Passive telemetry — no control-flow impact |
| **Email** | Mock provider → Resend / Mailgun (roadmap) | Verification + password reset emails |

---

## Project Structure

```
Homelab/
├── core/                               # Core infrastructure layer
│   ├── docker-compose.yml              # PostgreSQL + MinIO + auth-service + Caddy
│   └── Caddyfile                       # Reverse proxy config
│
└── auth-service/                       # Main BaaS platform service
    ├── Dockerfile                      # Non-root Python 3.11 container
    ├── docker-compose.yml              # Standalone service compose
    ├── requirements.txt                # Python dependencies
    │
    ├── app/
    │   ├── main.py                     # FastAPI app + lifespan + DI wiring
    │   ├── config.py                   # Pydantic settings (env-driven)
    │   ├── auth.py                     # JWT creation + verification
    │   ├── database.py                 # DB bootstrap helpers
    │   │
    │   ├── api/                        # HTTP layer — routes + service layers
    │   │   ├── routes.py               # Platform API routes
    │   │   ├── auth_routes.py          # Platform auth (login/signup)
    │   │   ├── baas_project_routes.py  # BaaS project management
    │   │   ├── baas_auth_routes.py     # End-user auth per project
    │   │   ├── baas_storage_routes.py  # File storage API
    │   │   ├── dependencies.py         # FastAPI DI providers
    │   │   ├── rate_limiter.py         # Sliding-window rate limiter
    │   │   └── service.py              # Internal API service layer
    │   │
    │   ├── platform/                   # Core workflow engines (The Brain)
    │   │   ├── audit/                  # Immutable audit trail engine
    │   │   ├── backup/                 # Backup workflow engine
    │   │   ├── deployment/             # Deploy / stop / restart engine
    │   │   ├── events/                 # Event publish / route engine
    │   │   ├── health/                 # Health aggregation engine
    │   │   ├── lifecycle/              # Project state machine
    │   │   ├── operations/             # Platform Operations Coordinator
    │   │   ├── restore/                # Restore workflow engine
    │   │   └── validation/             # Pre-flight validation engine
    │   │
    │   ├── providers/                  # Infrastructure implementations
    │   │   ├── deployment/             # DockerDeploymentProvider
    │   │   └── storage/                # LocalStorageProvider
    │   │
    │   ├── security/                   # Auth + authorization
    │   │   ├── authorization.py        # RBAC enforcement
    │   │   ├── permissions.py          # Role → permission mappings
    │   │   └── hardening/              # Security headers, input hardening
    │   │
    │   ├── storage/                    # Persistence adapters
    │   │   └── providers/
    │   │       ├── sqlite.py           # System database repositories
    │   │       └── sqlite_tenant.py    # Per-tenant DB connection factory
    │   │
    │   ├── observability/              # Structured logging
    │   ├── reliability/                # Retry + circuit breaker patterns
    │   ├── services/                   # Email + external service adapters
    │   └── identity/                   # Identity context models
    │
    └── docs/
        ├── ARCHITECTURE_V1.md          # Architecture constitution
        ├── MASTER_25_PHASE_ROADMAP.md  # Source-of-truth roadmap
        ├── DEPLOYMENT.md               # Production deployment guide
        └── PHASE10_ROADMAP.md          # Phase 10 reference
```

---

## API Surface

All routes are prefixed under `/api/v1`. Full interactive docs available at `/docs` when the service is running.

### Platform Auth

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a platform account |
| `POST` | `/auth/login` | Login, receive JWT |
| `POST` | `/auth/logout` | Invalidate session |
| `GET` | `/auth/me` | Get current user profile |

### BaaS — Projects

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/baas/projects` | Create a new project |
| `GET` | `/baas/projects` | List your projects |
| `GET` | `/baas/projects/{id}` | Get project details |
| `DELETE` | `/baas/projects/{id}` | Delete a project |
| `POST` | `/baas/projects/{id}/api-keys` | Generate an API key (shown once) |
| `GET` | `/baas/projects/{id}/api-keys` | List API key metadata |
| `DELETE` | `/baas/projects/{id}/api-keys/{kid}` | Revoke an API key |
| `POST` | `/baas/projects/{id}/members` | Invite a team member |
| `PATCH` | `/baas/projects/{id}/members/{uid}` | Change a member's role |
| `DELETE` | `/baas/projects/{id}/members/{uid}` | Remove a member |

### BaaS — Database

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/baas/projects/{id}/db/tables` | Create a table |
| `GET` | `/baas/projects/{id}/db/tables` | List tables |
| `DELETE` | `/baas/projects/{id}/db/tables/{table}` | Drop a table |
| `POST` | `/baas/projects/{id}/db/{table}/rows` | Insert a row |
| `GET` | `/baas/projects/{id}/db/{table}/rows` | Select rows |
| `PATCH` | `/baas/projects/{id}/db/{table}/rows/{rowid}` | Update a row |
| `DELETE` | `/baas/projects/{id}/db/{table}/rows/{rowid}` | Delete a row |

### BaaS — End-User Auth (per project)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/baas/projects/{id}/auth/signup` | Sign up an end-user |
| `POST` | `/baas/projects/{id}/auth/login` | Log in an end-user |
| `POST` | `/baas/projects/{id}/auth/logout` | Log out |
| `POST` | `/baas/projects/{id}/auth/verify-email` | Verify email token |
| `POST` | `/baas/projects/{id}/auth/forgot-password` | Request a password reset link |
| `POST` | `/baas/projects/{id}/auth/reset-password` | Submit new password |

### BaaS — Storage

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/baas/projects/{id}/storage/upload` | Upload a file |
| `GET` | `/baas/projects/{id}/storage/{path}` | Download a file |
| `DELETE` | `/baas/projects/{id}/storage/{path}` | Delete a file |
| `GET` | `/baas/projects/{id}/storage` | List files + metadata |

### Platform Operations

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/projects/{id}/deploy` | Deploy a project |
| `POST` | `/projects/{id}/stop` | Stop a project |
| `POST` | `/projects/{id}/restart` | Restart a project |
| `GET` | `/projects/{id}/health` | Get health status |
| `POST` | `/projects/{id}/backup` | Create a backup |
| `POST` | `/projects/{id}/restore` | Restore from backup |
| `GET` | `/health` | Platform readiness probe |

---

## Getting Started

### Prerequisites

- Docker v20+ and Docker Compose v2+
- Git

### Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/sharancode3/Homelab.git
cd Homelab

# 2. Configure secrets
cp auth-service/.env.example auth-service/.env
# Edit auth-service/.env — set PLATFORM_SECRET_KEY to a strong random value

# 3. Spin everything up (PostgreSQL + MinIO + auth-service + Caddy)
cd core
docker compose up -d --build

# 4. Verify the platform is healthy
curl http://localhost/health
# Response: {"status": "ok", "version": "1.0.0"}

# 5. Explore the interactive API docs
open http://localhost/docs
```

### Standalone Auth Service (development)

```bash
cd auth-service
docker compose up -d --build

# Follow logs
docker compose logs -f platform-orchestrator
```

---

## Configuration

All settings are driven by environment variables — no config files with secrets:

| Variable | Default | Description |
|---|---|---|
| `PLATFORM_ENVIRONMENT` | `production` | `development` / `staging` / `production` |
| `PLATFORM_DEBUG` | `false` | Enable debug-level structured logs |
| `PLATFORM_API_HOST` | `0.0.0.0` | FastAPI bind address |
| `PLATFORM_API_PORT` | `8000` | FastAPI bind port |
| `PLATFORM_STORAGE_PATH` | `/var/lib/auth-service/data` | Persistent data directory |
| `PLATFORM_SECRET_KEY` | *(required)* | JWT signing key — **change this in production** |
| `CORS_ALLOWED_ORIGINS` | `*` | Comma-separated allowed origins for CORS |

> **Production note:** Never commit `PLATFORM_SECRET_KEY` to version control. Use a secrets manager or inject it at deploy time.

---

## Security Model

Security is built into every layer — not bolted on at the end:

| Concern | Implementation |
|---|---|
| **Password hashing** | Argon2id via passlib — the gold standard for memory-hard password hashing |
| **Sessions** | Short-lived JWT access tokens signed with HMAC-SHA256 |
| **API Keys** | Formatted as `pk_live_xxx`, revealed once at creation, stored as a salted hash — never recoverable |
| **Tenant isolation** | Separate SQLite database file per project — no shared tables, no schema-prefix tricks |
| **Authorization** | Explicit `Identity → Project → Permission → Resource` chain enforced on every request |
| **Rate limiting** | Sliding-window limiter on all auth, signup, reset, API key, and data endpoints |
| **Input validation** | Pydantic v2 on all request bodies; parameterized queries only — zero raw SQL concatenation |
| **Token security** | Email verification and password reset tokens are single-use, time-limited, and hashed in the DB |
| **Container security** | Non-root `appuser` inside the container — no capability escalation |
| **Secrets** | All secrets via environment variables — no hardcoded values anywhere in source |

---

## Build Philosophy

> *"We do not skip verification to hit a date. The objective is not merely to finish code — it is to prove the system works with a real external application."*

### Engineering Workflow

Every phase follows this invariant pipeline without exception:

```
Roadmap definition
  → Read-only preflight
  → Gap analysis
  → Boundary audit
  → Open decisions
  → Implementation plan
  → Explicit approval
  → Implementation
  → Tests
  → Review
  → Real verification  (never mocked when real verification is available)
  → Fixes
  → Final verification
  → Commit + push
  → Locked checkpoint
  → Next-phase preflight
```

### Architecture Rules

- Engines own workflows, not infrastructure.
- Adapters own infrastructure, not workflows.
- Coordinators own orchestration, not business logic.
- No engine may import a provider directly — always through the adapter interface.
- No endpoint may bypass the authorization chain.
- No verification may be faked — real tests or real probes, always.
- No heavy infrastructure (Redis, Kafka, Kubernetes) introduced before the phase that explicitly requires it.
- The 4 GB ThinkPad RAM constraint is a first-class design input, not a limitation to work around later.

---

## Current Status and Roadmap

### Completed and Locked

| Phase | Capability | Commit |
|---|---|---|
| 9A | Core Platform Engines (8 engines + Coordinator) | — |
| 10 | Production Architecture (FastAPI, Docker, adapters) | — |
| 10.5 | Real Deployment Smoke Test | — |
| 11.1 | Developer Identity / Auth | — |
| 11.2 | Projects + Ownership | `3908b13` |
| 11.3 | Team Membership + RBAC | `b3d41f6` |
| 11.4 | Project API Keys (`pk_live_xxx`) | `28cd995` |
| 11.5 | Database / Tables / Data API | `a2c2700` |
| 11.6 | Team Collaboration | `5fb81c0` |
| 12 | Developer API + Rate Limiting | `77dccb1` / `9ac43dc` |
| 13 | Database / Data Service Integration | `99c7535` |
| 14.1 | End-User Auth Service (per project) | `33e4e48` |
| 14.2 | BaaS Storage Service | `1ed2410` |
| 14.3 | Deployment Integration | `874a107` |
| 14.4 | Monitoring | `feb33f3` |
| **15** | **Security + Reliability Audit** | `21e2e02` |

### Upcoming

| Phase | Capability | Status |
|---|---|---|
| **16** | **Dashboard / Frontend** — React + Vite + TypeScript + Tailwind | **NEXT** |
| 16.1–16.6 | Account UI, Project UI, Team UI, Database UI, API Key UI, Deployment UI | Planned |
| 17 | Frontend Deployment + Public Access via Cloudflare Tunnel | Planned |
| 18 | Full Adversarial Security Review | Planned |
| 19 | Reliability + Failure Testing (chaos scenarios) | Planned |
| 20 | Performance + Resource Testing (measured quotas on ThinkPad hardware) | Planned |
| 21 | Real External Application Test — complete developer journey end-to-end | Planned |
| 22 | Bug-Fix / Integration Sprint | Planned |
| 23 | Production Readiness (code cleanup, HTTPS hardening, CORS, security headers) | Planned |
| 24 | Developer Documentation | Planned |
| 25 | Final Release Verification Gate | Planned |

> **SDK note:** The Python SDK — and later JavaScript/TypeScript, Flutter, and Android SDKs — is a required capability that has not yet been executed. It will be built and verified before the Phase 21 external application test.

---

## Future Scope

### Near-Term  (Phases 16–21)

- **Developer Dashboard** — A full React + TypeScript web UI where developers manage projects, browse and edit database tables, inspect file storage, view deployment status, manage team members, and rotate API keys — all from a browser, backed by the same secured APIs.
- **Cloudflare Tunnel** — Zero-trust public exposure via `Internet → Cloudflare → Cloudflare Tunnel → ThinkPad`, keeping PostgreSQL and all internal services completely off the public internet.
- **Python SDK** — `pip install homelab-sdk` — a typed client wrapping auth, database, storage, and deployment APIs, with error handling, retries, and sensible defaults out of the box.

### Mid-Term  (Phases 18–23)

- **Multi-SDK support** — JavaScript/TypeScript SDK for web, Flutter SDK for mobile, Android SDK for native apps — each matching the Python SDK's design.
- **PostgreSQL migration** — Replace per-project SQLite files with PostgreSQL schemas, unlocking connection pooling, full transactions, concurrent writes, and production-grade durability.
- **MinIO / S3-compatible storage** — Swap `LocalStorageProvider` for a MinIO-backed provider, enabling bucket-level isolation, pre-signed URLs, and gigabyte-scale storage without a cloud dependency.
- **Full adversarial security review** — Systematic attack testing: brute-force, IDOR, SQL injection, path traversal, token replay, privilege escalation — across every API surface.
- **Measured performance quotas** — Empirically benchmark RAM, CPU, disk I/O, and API latency at 10, 20, 50, and 100 concurrent projects on the ThinkPad before setting any resource limits.

### Long-Term Vision

- **Kubernetes deployment provider** — A `KubernetesDeploymentProvider` alongside the existing Docker provider, enabling projects to run as pods with defined CPU and memory limits.
- **Real-time subscriptions** — WebSocket or SSE endpoints that let client applications subscribe to live database change events (inspired by Supabase Realtime).
- **OpenTelemetry + Prometheus + Grafana** — Replace the current structured logger with a full observability stack: distributed traces, metrics dashboards, and alerting.
- **Multi-node support** — Extend the platform beyond a single ThinkPad to a small homelab cluster, enabling horizontal scaling without cloud infrastructure.
- **Plugin / provider marketplace** — Allow third-party auth providers, storage backends, email providers, and deployment targets to be registered via the existing Adapter interface — zero core changes required.
- **Project-level webhooks** — Let developers subscribe to platform events (deploy completed, backup failed, storage quota nearing limit) and receive outbound HTTP callbacks.

---

## Contributing

This is a personal engineering project built with first principles and no shortcuts. Before contributing, read the [Architecture Constitution](./auth-service/docs/ARCHITECTURE_V1.md) and the [Master 25-Phase Roadmap](./auth-service/docs/MASTER_25_PHASE_ROADMAP.md) — every change must respect the established engine boundaries, authorization invariants, and verification standards.

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

<p align="center">
  Built with ⚡ on a ThinkPad. No cloud. No compromise.
</p>
