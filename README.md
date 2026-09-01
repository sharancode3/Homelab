# Homelab Platform Orchestrator & Backend-as-a-Service (BaaS)

A self-hosted, multi-tenant developer platform and Backend-as-a-Service engineered specifically for resource-constrained edge environments (single-node 4 GB RAM hardware). Built from first principles to deliver robust tenant isolation, modular orchestration engines, relational database provisioning, local object storage, multi-role RBAC, and an external Python SDK with a strict 256 MB memory envelope.

---

## System Overview

| Parameter | Specification |
|---|---|
| Platform Architecture | Three-Plane Engine/Adapter/Coordinator Model |
| Target Host Constraint | Single-Node Edge Host (4 GB RAM, 2 Cores) |
| Orchestrator Memory Limit | Strict 256 MB RAM Constraint (`docker-compose.yml`) |
| Control & Management API | FastAPI (Python 3.10+) with Pydantic Schema Validation |
| Management Dashboard | React 18, TypeScript, Vite, Tailwind CSS SPA |
| Edge Ingress & Gateway | Caddy 2 Reverse Proxy with Cloudflare Zero Trust Tunnel |
| Tenant Isolation Model | Dedicated Per-Project SQLite Database (WAL Mode) & Partitioned Blob Storage |
| Authentication Planes | Developer Management JWT, Project API Key, Project End-User Pool JWT |
| Cryptographic Standard | PyJWT HS256 Symmetric Signing, Argon2id Password Hashing, SHA-256 API Keys |
| Client SDK | Python SDK (`homelab_sdk`) with Typed Interfaces & Exception Hierarchy |
| Verification Gate | 25-Phase Rigorous Roadmap with Chaos, Load, and E2E Proofs |

---

## Architectural Principles

1. **Strict Three-Plane Isolation:** The system isolates the Management Plane (developer administration, project creation, member RBAC), the Data Plane (database rows, file blobs via API keys), and the End-User Identity Plane (project-isolated consumer users).
2. **Deterministic Embedded Persistence:** Heavy, multi-gigabyte broker and database dependencies (e.g., standalone PostgreSQL/Redis clusters) are eliminated in favor of high-performance, per-tenant SQLite databases configured with Write-Ahead Logging (WAL), busy timeout handlers, and dedicated local directory sandboxes.
3. **Resilient Engine/Coordinator Pattern:** Operational workflows (deployment lifecycle, backups, restores, health inspections, validation) are isolated in dedicated engines managed by a centralized `PlatformOperationsCoordinator` enforcing mutual exclusion locks and idempotency per project.
4. **Defense in Depth & Rate Limiting:** All inbound network traffic passes through multi-layered Token Bucket rate limiters (per-IP, per-API-Key, and anti-brute-force identity buckets), application-level security headers, path sanitization, and SQL identifier whitelisting.
5. **Verified Hardware Safety Margins:** Validated under continuous monitoring up to 100 concurrent tenant projects and 1,410 burst requests on 4 GB RAM hardware with zero OOM events, zero 5xx server errors, zero lockouts, and an 84.5 ms p50 latency baseline.

---

## Architecture Diagrams

### 1. High-Level Edge Ingress and Network Topology

```mermaid
graph TD
    subgraph Public Internet
        DevClient[Developer / Browser]
        ExtApp[External Application / Python SDK]
        EndUser[End Consumer]
    end

    subgraph Edge Security & Ingress
        CFTunnel[Cloudflare Zero Trust Tunnel]
        Caddy[Caddy 2 Reverse Proxy Gateway]
    end

    subgraph Homelab Host [Single-Node ThinkPad - 4 GB RAM]
        StaticSPA[React 18 / Vite Dashboard SPA]
        Orchestrator[FastAPI Platform Orchestrator - 256MB Cap]
        
        subgraph Data Storage Directory [/var/lib/auth-service/data]
            CoordDB[(Coordination & Auth DBs)]
            
            subgraph Project A Directory
                ProjADB[(Project A SQLite DB)]
                ProjABlobs[Project A File Storage]
            end
            
            subgraph Project B Directory
                ProjBDB[(Project B SQLite DB)]
                ProjBBlobs[Project B File Storage]
            end
        end
    end

    DevClient -->|HTTPS / WSS| CFTunnel
    ExtApp -->|HTTPS API Requests| CFTunnel
    EndUser -->|HTTPS Auth / Data| CFTunnel

    CFTunnel -->|Encrypted Host Pipe| Caddy
    Caddy -->|/ | StaticSPA
    Caddy -->|/api/v1/baas/*| Orchestrator
    Caddy -->|/api/v1/auth/*| Orchestrator
    Caddy -.->|Block /api/v1/platform/*| Caddy

    Orchestrator --> CoordDB
    Orchestrator --> ProjADB
    Orchestrator --> ProjABlobs
    Orchestrator --> ProjBDB
    Orchestrator --> ProjBBlobs
```

---

### 2. Multi-Plane Security and Authentication Model

```mermaid
graph LR
    subgraph Inbound Authentication Streams
        DevReq[Developer Request]
        SDKReq[SDK Data Request]
        UserReq[End-User Request]
    end

    subgraph Security Layer
        JWTDevValidator[JWT Validator: aud=developer]
        APIKeyValidator[API Key Validator: SHA-256 Hash Compare]
        JWTUserValidator[JWT Validator: aud=end_user]
    end

    subgraph Scope & Boundary
        AdminBoundary[Management Plane: Projects, Members, Schemas]
        DataBoundary[Data Plane: Project-Specific Tables & Objects]
        UserBoundary[Identity Pool: Project-Specific User Store]
    end

    DevReq -->|Authorization: Bearer <Token>| JWTDevValidator
    JWTDevValidator -->|RBAC: Owner / Admin / Dev / Viewer| AdminBoundary

    SDKReq -->|X-Project-API-Key: pk_live_***| APIKeyValidator
    APIKeyValidator -->|Bound to project_id| DataBoundary

    UserReq -->|Authorization: Bearer <Token>| JWTUserValidator
    JWTUserValidator -->|Bound to project_id & user_id| UserBoundary
```

---

### 3. Internal Platform Orchestrator Architecture

```mermaid
graph TB
    subgraph API & Routing Layer
        FastAPIApp[FastAPI Application Instance]
        RateLimiter[Token Bucket Rate Limiter]
        AuthMiddleware[Security Headers & CORS Middleware]
        RouteAuth[Auth Routes]
        RouteBaaS[BaaS Project Routes]
        RouteStorage[BaaS Storage Routes]
        RouteHealth[Platform Health Routes]
    end

    subgraph Core Service Coordination
        BaaSService[BaaS Project Service Layer]
        BaaSAuthService[BaaS Auth Service Layer]
        BaaSStorageService[BaaS Storage Service Layer]
        APIService[Internal API Service Layer]
        Coordinator[Platform Operations Coordinator]
    end

    subgraph Operational Engines
        LifecycleEng[Lifecycle Manager]
        ValidationEng[Validation Engine]
        DeploymentEng[Deployment Engine]
        BackupEng[Backup Engine]
        RestoreEng[Restore Engine]
        HealthEng[Health Engine]
        AuditEng[Audit Engine]
        EventEng[Event Engine]
    end

    subgraph Adapters & Repositories
        DockerAdapter[Docker Deployment Provider]
        LocalStorageAdapter[Local Disk Storage Provider]
        TenantConnFactory[SQLite Tenant Connection Factory]
        TenantDBManager[Tenant Database Manager]
        AuditRepo[SQLite Audit Repository]
        HistoryRepo[SQLite History Repository]
    end

    FastAPIApp --> AuthMiddleware
    AuthMiddleware --> RateLimiter
    RateLimiter --> RouteAuth
    RateLimiter --> RouteBaaS
    RateLimiter --> RouteStorage
    RateLimiter --> RouteHealth

    RouteBaaS --> BaaSService
    RouteAuth --> BaaSAuthService
    RouteStorage --> BaaSStorageService

    BaaSService --> APIService
    BaaSService --> TenantDBManager
    BaaSAuthService --> TenantConnFactory
    BaaSStorageService --> LocalStorageAdapter

    APIService --> Coordinator
    Coordinator --> LifecycleEng
    Coordinator --> ValidationEng
    Coordinator --> DeploymentEng
    Coordinator --> BackupEng
    Coordinator --> RestoreEng
    Coordinator --> HealthEng
    Coordinator --> AuditEng
    Coordinator --> EventEng

    DeploymentEng --> DockerAdapter
    Coordinator --> AuditRepo
    Coordinator --> HistoryRepo
```

---

### 4. Multi-Tenant Physical Data Isolation Boundary

```mermaid
graph TD
    subgraph Host Root Directory: /var/lib/auth-service/data
        subgraph Shared Platform Metadata
            users[(users.db: Developer Accounts)]
            authz[(authz.db: Team RBAC & API Keys)]
            projects[(projects.db: Registry & Lifecycles)]
            audit[(audit.db: Immutable Audit Logs)]
            history[(history.db: Operation Plans & Runs)]
            revocations[(revocations.db: JWT JTI Denylist)]
        end

        subgraph Project Isolation Sandbox: projects/
            subgraph Tenant Alpha: projects/proj_001/
                AlphaDB[(data.db: Tables & End-Users)]
                AlphaStorage[storage/: Blobs & Attachments]
            end

            subgraph Tenant Beta: projects/proj_002/
                BetaDB[(data.db: Tables & End-Users)]
                BetaStorage[storage/: Blobs & Attachments]
            end
        end
    end

    classDef shared fill:#2d3748,stroke:#4a5568,color:#fff;
    classDef tenant fill:#1a365d,stroke:#2b6cb0,color:#fff;
    class users,authz,projects,audit,history,revocations shared;
    class AlphaDB,AlphaStorage,BetaDB,BetaStorage tenant;
```

---

### 5. End-to-End Request and Execution Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Client as SDK / External App
    participant Caddy as Caddy Gateway
    participant RL as Rate Limiter
    participant Sec as Auth & RBAC
    participant Router as Project Router
    participant Tenant as Tenant Factory
    participant DB as SQLite Tenant DB

    Client->>Caddy: POST /api/v1/baas/projects/{proj_id}/tables/tasks/rows
    Note over Client,Caddy: Header: X-Project-API-Key: pk_live_***
    Caddy->>RL: Forward HTTP Request
    RL->>RL: Consume Token (10 req/s, Burst 100)
    RL->>Sec: Rate limit passed
    Sec->>Sec: Parse key, SHA-256 verify against authz.db
    Sec->>Sec: Assert project_id match & key active
    Sec->>Router: Inject validated project context
    Router->>Router: Validate table & column identifier regex
    Router->>Tenant: Acquire connection for proj_id
    Tenant->>DB: Open data.db (WAL Mode, Timeout 5.0s)
    DB->>DB: Execute parameterized INSERT query
    DB-->>Tenant: Row ID returned
    Tenant-->>Router: Commit & Release connection
    Router-->>Client: 200 OK {"id": "row_123", "status": "created"}
```

---

### 6. Project Lifecycle and Operational State Machine

```mermaid
stateDiagram-v2
    [*] --> Registered: Developer Creates Project
    Registered --> Initialized: Run Validation Engine
    Initialized --> Provisioned: Allocate SQLite DB & Storage Directory
    Provisioned --> Active: Complete Health & Baseline Check
    Active --> Paused: Explicit Stop / Pause Request
    Paused --> Active: Resume / Redeploy Operation
    Active --> Failed: Engine Failure / Health Degraded
    Paused --> Failed: Storage Error / Corruption
    Failed --> Active: Restore from Validated Backup
    Active --> [*]: Project Teardown / Deletion
```

---

## Repository Structure

```text
Homelab/
├── README.md                               # Authoritative Platform Documentation
├── core/                                   # Host Ingress and Docker Orchestration
│   ├── Caddyfile                           # Edge Routing, Header Ingestion & API Security Gate
│   ├── docker-compose.yml                  # Production Container Setup (Auth, Caddy, Cloudflare, MinIO, PG)
│   └── .env.example                        # Template Environment Configuration
│
├── auth-service/                           # Core Platform Orchestrator (FastAPI)
│   ├── Dockerfile                          # Production Multi-Stage Python Runtime
│   ├── requirements.txt                    # Core Production Dependencies
│   ├── requirements-dev.txt                # Testing and Linting Dependencies
│   ├── app/
│   │   ├── main.py                         # FastAPI App, Lifespan Hooks & Global Middleware
│   │   ├── auth.py                         # Password Hashing (Argon2id) & JWT Generation (HS256)
│   │   ├── config.py                       # Pydantic Settings & Environment Loading
│   │   ├── project_registry_manager.py     # Tenant Project Management & State Machine
│   │   ├── api/                            # HTTP Routing & Request Handlers
│   │   │   ├── auth_routes.py              # Developer Authentication Endpoints
│   │   │   ├── baas_project_routes.py      # Project, Table, Row, Team & Key Routes
│   │   │   ├── baas_auth_routes.py         # End-User Identity Pool Endpoints
│   │   │   ├── baas_storage_routes.py      # Multipart Blob Upload & Stream Download
│   │   │   ├── rate_limiter.py             # Asynchronous Token Bucket Rate Limiting
│   │   │   └── dependencies.py             # Dependency Injection & RBAC Enforcement
│   │   ├── platform/                       # Deterministic Operational Engines
│   │   │   ├── operations/                 # Coordinator, Mutex Locks & Operation Plans
│   │   │   ├── lifecycle/                  # Lifecycle Engine & State Validation
│   │   │   ├── deployment/                 # Deployment Engine & Strategy Execution
│   │   │   ├── backup/                     # Backup Engine & Manifest Tracking
│   │   │   ├── restore/                    # Restore Engine & Consistency Validation
│   │   │   ├── health/                     # SQLite Latency & Disk Space Health Probes
│   │   │   ├── audit/                      # Tamper-Evident Immutable Audit Log Engine
│   │   │   ├── events/                     # Synchronous Event Dispatcher & Bus
│   │   │   └── validation/                 # Preflight & Schema Validation Engine
│   │   ├── storage/providers/
│   │   │   ├── sqlite.py                   # Coordination SQLite Repositories
│   │   │   └── sqlite_tenant.py            # Isolated Tenant DB Manager & Connection Factory
│   │   ├── providers/
│   │   │   ├── deployment/docker_provider.py # Docker Deployment Interface Adapter
│   │   │   └── storage/local_storage.py    # Sandboxed Filesystem Blob Storage Adapter
│   │   └── observability/                  # Structured Logging, Metrics Registry & Tracing
│   │
│   ├── dashboard/                          # Management Web Console (SPA)
│   │   ├── src/
│   │   │   ├── App.tsx                     # Top-Level Router & Layout Container
│   │   │   ├── features/                   # Domain Feature Modules
│   │   │   │   ├── auth/                   # Developer Login & Signup Forms
│   │   │   │   ├── projects/               # Project Creation, Overview & Switcher
│   │   │   │   ├── database/               # Table Schema Builder & Live Data Grid
│   │   │   │   ├── storage/                # File Browser, Upload Modal & Quota Meters
│   │   │   │   ├── apikeys/                # API Key Generation & One-Time Reveal Dialog
│   │   │   │   ├── team/                   # Member Invites & RBAC Role Selector
│   │   │   │   └── deployment/             # Deployment Status, Backup Trigger & History
│   │   │   ├── contexts/                   # AuthContext & ProjectContext State Providers
│   │   │   └── hooks/                      # Custom React Hooks for API Interaction
│   │   ├── package.json                    # Dashboard Node Dependencies
│   │   └── vite.config.ts                  # Vite Build Configuration
│   │
│   ├── docs/                               # Engineering Documentation & Roadmaps
│   │   ├── MASTER_25_PHASE_ROADMAP.md      # Permanent 25-Phase Verification Control Document
│   │   ├── ARCHITECTURE_V2.md              # Validated Architecture & Engine Boundaries
│   │   ├── API_REFERENCE.md                # Comprehensive Endpoint Specification
│   │   ├── SECURITY_AND_LIMITS.md          # Cryptographic Rules, Quotas & Hardware Limits
│   │   ├── DEVELOPER_GUIDE.md              # External Application Developer Onboarding
│   │   ├── phase19_chaos_runbook.md        # Chaos Engineering & Infrastructure Resilience Runbook
│   │   ├── phase20_performance_audit.md    # 100-Project Performance Load Audit Decision
│   │   └── phase21_e2e_verification.md     # Full E2E Verification Record
│   │
│   └── tests/                              # Comprehensive Test Suite (100+ Tests)
│       ├── security/                       # Brute-force, SQL injection, IDOR & leakage tests
│       ├── performance/                    # Load generation, telemetry monitors & quota tests
│       └── integration_chaos/              # Automated fault-injection & recovery suites
│
├── sdk-python/                             # Official Homelab Python SDK (`homelab_sdk`)
│   ├── pyproject.toml                      # Standard Packaging Metadata
│   ├── homelab_sdk/
│   │   ├── client.py                       # Top-Level `HomelabClient` Entrypoint
│   │   ├── exceptions.py                   # Typed Exception Hierarchy (401, 403, 404, 429, 500)
│   │   └── api/                            # Domain Client Implementations
│   │       ├── admin.py                    # Developer Authentication & Registration
│   │       ├── projects.py                 # Project Lifecycle, Deployment, Backup & Logs
│   │       ├── teammates.py                # Member Add, List, Update & Remove
│   │       ├── apikeys.py                  # API Key Generation, Listing & Revocation
│   │       ├── schema.py                   # Table Creation & Schema Inspection
│   │       ├── db.py                       # Parameterized Row CRUD Operations
│   │       ├── storage.py                  # File Upload, Download & Deletion
│   │       └── auth.py                     # Project End-User Pool Authentication
│   └── tests/                              # SDK Unit & Platform Integration Tests
│
└── external-app/                           # Verified Real-World External Consumer Application
    ├── todo_app.py                         # `TaskManager` Standalone Domain Application
    ├── run_e2e.py                          # Full 25-Phase End-to-End Workflow Execution
    └── tests/test_todo_app.py              # Application-Level Unit Test Suite
```

---

## Subsystem Deep Dives

### 1. Identity, Authentication, and RBAC

The platform establishes three segregated authentication boundaries:

```text
+---------------------------------------------------------------------------------------------------+
| MANAGEMENT PLANE (Developer Account)                                                              |
| Header: Authorization: Bearer <Developer JWT>                                                     |
| Token Claims: sub=<user_id>, aud="developer", exp=30min, jti=<uuid>                               |
| Access: Project Provisioning, Team Management, Key Generation, Deployments, Backups               |
+---------------------------------------------------------------------------------------------------+
| DATA & STORAGE PLANE (External Application)                                                       |
| Header: X-Project-API-Key: pk_live_<key_id>_<secret>                                              |
| Verification: SHA-256(secret) == authz.db[key_id].secret_hash                                     |
| Access: Scoped strictly to project tables, rows, and object storage                               |
+---------------------------------------------------------------------------------------------------+
| END-USER IDENTITY PLANE (Project Consumers)                                                       |
| Header: Authorization: Bearer <End-User JWT>                                                      |
| Token Claims: sub=<end_user_id>, aud="end_user", project_id=<proj_id>, exp=30min                  |
| Access: Isolated end-user data within the consumer application                                    |
+---------------------------------------------------------------------------------------------------+
```

#### Team Member RBAC Matrix

| Role | View Resources | Insert/Update Data | Manage Schemas | Trigger Deploy/Stop | Trigger Backup/Restore | Manage Team & Keys |
|---|---|---|---|---|---|---|
| **OWNER** | Allowed | Allowed | Allowed | Allowed | Allowed | Allowed |
| **ADMIN** | Allowed | Allowed | Allowed | Allowed | Allowed | Restricted (Cannot delete project) |
| **DEVELOPER**| Allowed | Allowed | Allowed | Allowed | Denied | Denied |
| **VIEWER** | Allowed | Denied | Denied | Denied | Denied | Denied |

---

### 2. Tenant Database Service (Data Plane)

- **Storage Engine:** Dedicated SQLite database file per project located at `/var/lib/auth-service/data/projects/{project_id}/data.db`.
- **Concurrency Mode:** Configured with `PRAGMA journal_mode=WAL` (Write-Ahead Logging) to permit simultaneous non-blocking reads while writes occur.
- **Busy Timeout:** 5,000 ms busy handler to handle concurrent write bursts gracefully without throwing lock exceptions.
- **SQL Injection Defense:**
  - Table and column names are validated strictly against `^[a-zA-Z_][a-zA-Z0-9_]{0,63}$`.
  - Reserved prefixes (`sqlite_`, `_baas_`) are forbidden for user tables.
  - All query values are bound exclusively via parameterized SQL placeholders (`?`).
- **Supported Data Types:** `TEXT`, `INTEGER`, `REAL`, `JSON` (stored internally as validated JSON text).

---

### 3. Tenant Object Storage Service

- **Storage Engine:** Sandboxed local directory storage partitioned by project: `/var/lib/auth-service/data/projects/{project_id}/storage/`.
- **Metadata Store:** Tracked in the tenant's isolated database within the `_baas_objects` table (recording file ID, original filename, MIME type, size in bytes, SHA-256 checksum, uploader ID, and creation timestamp).
- **Enforced Constraints:**
  - `storage_max_file_size_bytes`: **5 MB** per individual file upload.
  - `storage_max_project_quota_bytes`: **100 MB** total aggregated storage per project.
- **Streaming Transfer:** Large file downloads utilize chunked `StreamingResponse` streams with explicit `Content-Disposition` headers to preserve memory bounds.

---

### 4. Platform Operations Coordinator & Engines

All infrastructure and lifecycle actions run through the centralized `PlatformOperationsCoordinator`:

- **Mutual Exclusion Locking:** An internal threading lock (`_active_operations`) guarantees that only one mutating operation (deploy, backup, restore, restart) can execute on a single project at any given time, rejecting concurrent attempts with HTTP 409 Conflict.
- **Correlation & Tracing:** Every operational request is assigned an immutable `operation_id` (`op_...`) and `correlation_id` (`corr_...`), tracked across structured log events and persisted in `history.db`.
- **Reliability & Event DLQ:** Failed event dispatches are routed through an internal `DeadLetterQueue` managed by the `EventReliabilityManager` to prevent event loss.

---

### 5. Health Monitoring & Observability

- **Endpoint:** `GET /api/v1/health/platform` (also aliased at `/health`).
- **Health Evaluators:**
  - **SQLite Latency Probe:** Executes a heartbeat query against tenant databases. Latencies exceeding 500 ms trigger degraded health state.
  - **Host Disk Free Space:**
    - Space < 500 MB: System status changes to `DEGRADED`.
    - Space < 100 MB: System status changes to `UNHEALTHY` (returns HTTP 503).
- **Resource Boundary:** Continuously monitors RAM consumption to maintain compliance with the 256 MB Docker container ceiling.

---

### 6. Rate Limiting and Brute-Force Protection

The platform implements an in-memory Token Bucket algorithm with automatic Least-Recently-Used (LRU) bucket eviction (10,000 maximum tracking keys):

- **Data Plane Bucket:** 10 tokens/second refill rate, burst capacity of 100 tokens (keyed by API key).
- **Control Plane Bucket:** 10 tokens/second refill rate, burst capacity of 100 tokens (keyed by client IP).
- **Auth Brute-Force Bucket:** 1 token/minute refill rate, burst capacity of 10 attempts (keyed simultaneously by IP and normalized email identity). Successful logins automatically clear the client IP counter.

---

## Python SDK Guide (`homelab-sdk`)

### 1. Installation

```bash
cd sdk-python
pip install -e .
```

### 2. Client Initialization

```python
from homelab_sdk.client import HomelabClient

# Management Plane Client (Admin / Developer)
admin_client = HomelabClient(
    base_url="https://api.yourdomain.com",
    developer_token="<DEVELOPER_BEARER_TOKEN>"
)

# Data Plane Client (Application Backend)
app_client = HomelabClient(
    base_url="https://api.yourdomain.com",
    project_id="proj_abcdef123456",
    api_key="pk_live_keyid_secrettoken"
)

# End-User Plane Client (Consumer User Context)
user_client = HomelabClient(
    base_url="https://api.yourdomain.com",
    project_id="proj_abcdef123456",
    end_user_token="<END_USER_BEARER_TOKEN>"
)
```

---

### 3. Management Plane Operations

```python
# 1. Register and Authenticate Developer
auth_res = admin_client.admin.register("dev@example.com", "lead_dev", "StrongPassword123")
login_res = admin_client.admin.login("dev@example.com", "StrongPassword123")
token = login_res["access_token"]

# 2. Provision a New Project
proj = admin_client.projects.create(name="Production API", slug="prod-api")
project_id = proj["project_id"]

# 3. Add a Teammate with RBAC Role
admin_client.teammates.add(project_id, "colleague@example.com", role="developer")

# 4. Generate a Persistent Project API Key
key_res = admin_client.apikeys.create(project_id, name="backend-service-key")
api_key = key_res["key"]  # Save this immediately; raw key is shown only once!

# 5. Define a Database Table Schema
admin_client.schema.create(
    project_id=project_id,
    table_name="orders",
    columns={
        "id": "text",
        "customer_id": "text",
        "amount": "real",
        "status": "text",
        "metadata": "json"
    }
)
```

---

### 4. Data Plane Operations (Database & Storage)

```python
# 1. Insert a Record
order_id = app_client.db.insert(
    project_id="proj_abcdef123456",
    table_name="orders",
    data={
        "id": "ord_9901",
        "customer_id": "cust_44",
        "amount": 149.99,
        "status": "pending",
        "metadata": {"source": "mobile_app", "discount": False}
    }
)

# 2. Query Records
orders = app_client.db.list(project_id="proj_abcdef123456", table_name="orders")

# 3. Update a Record
app_client.db.update(
    project_id="proj_abcdef123456",
    table_name="orders",
    row_id="ord_9901",
    data={"status": "fulfilled"}
)

# 4. Upload a File Blob (Up to 5 MB)
with open("invoice.pdf", "rb") as f:
    upload_res = app_client.storage.upload(
        project_id="proj_abcdef123456",
        filename="invoice_9901.pdf",
        content=f.read()
    )
file_id = upload_res["id"]

# 5. Download a File Blob
file_bytes = app_client.storage.download(
    project_id="proj_abcdef123456",
    file_id=file_id
)
```

---

### 5. End-User Authentication Plane

```python
# 1. Register End-User in Project Pool
app_client.auth.register(
    project_id="proj_abcdef123456",
    email="customer@example.com",
    password="CustomerPassword456"
)

# 2. Login End-User
user_session = app_client.auth.login(
    project_id="proj_abcdef123456",
    email="customer@example.com",
    password="CustomerPassword456"
)
user_jwt = user_session["access_token"]

# 3. Access Project as Authenticated End-User
user_client = HomelabClient(
    base_url="https://api.yourdomain.com",
    project_id="proj_abcdef123456",
    end_user_token=user_jwt
)
profile = user_client.auth.get_me(project_id="proj_abcdef123456")
```

---

## Management Dashboard UI

The platform includes a single-page management console located in `auth-service/dashboard/`:

- **Technology Stack:** React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons.
- **Capabilities:**
  - **Account & Security:** Developer login, user registration, JWT session persistence.
  - **Project Switcher:** Seamless switching across accessible tenant projects with strict role verification.
  - **Database Viewer:** Interactive table schema designer, column type selector, and live tabular data browser with insert, edit, and delete actions.
  - **Storage Manager:** Drag-and-drop file uploader, object directory inspector, size counters, and live quota usage progress bars.
  - **API Key Console:** One-time API key generator with cryptographic copy modals and revocation triggers.
  - **Team Collaboration:** Teammate invitation modal with dynamic RBAC role assignment (`OWNER`, `ADMIN`, `DEVELOPER`, `VIEWER`).
  - **Operations Console:** Real-time deployment trigger, container status indicator, health metrics viewer, and backup/restore history audit log.

```bash
# Running the Dashboard in Development Mode
cd auth-service/dashboard
npm install
npm run dev
```

---

## 25-Phase Verification Roadmap & Audit

The codebase strictly complies with the authoritative 25-Phase Roadmap. Every phase follows a rigorous progression from gap analysis to real verification locks:

| Phase | Description | Key Deliverables & Validation Scope | Status |
|---|---|---|---|
| **Phase 9A** | Core Platform Engines | Platform operations coordinator, engine adapters, and state machines | [LOCKED] |
| **Phase 10** | Production Architecture | Multi-container Compose architecture and internal repository interfaces | [LOCKED] |
| **Phase 10.5**| Real Deployment Smoke Test | Initial end-to-end containerized smoke validation | [LOCKED] |
| **Phase 11** | BaaS Foundation & Multi-Tenant RBAC | User registration, project ownership, team roles (Owner/Admin/Dev/Viewer) | [LOCKED] |
| **Phase 12** | Developer API & SDK Integration | API key hashing, public route contracts, and token bucket rate limiters | [LOCKED] |
| **Phase 12.5**| Rate Limiting & DoS Protection | In-memory token bucket implementation across IP, API Key, and Auth scopes | [LOCKED] |
| **Phase 13** | Database / Data Service | Per-project SQLite databases in WAL mode, table creation, parameterized CRUD | [LOCKED] |
| **Phase 14.1**| End-User Authentication Pool | Project-isolated user identity tables (`_baas_users`), JWT audience segregation | [LOCKED] |
| **Phase 14.2**| BaaS Storage Service | Sandboxed local storage provider, 5 MB file limit, 100 MB project quota | [LOCKED] |
| **Phase 14.3**| Deployment Integration | Operations engine binding to BaaS API with mutual exclusion locks | [LOCKED] |
| **Phase 14.4**| Health & Resource Monitoring | SQLite latency probe (<500 ms) and host disk capacity monitoring | [LOCKED] |
| **Phase 15** | Security & Reliability Audit | Comprehensive security boundaries, failure recovery, and audit trails | [LOCKED] |
| **Phase 16** | Dashboard / Frontend | React 18 / TypeScript SPA console with database, storage, and key management | [LOCKED] |
| **Phase 17** | Ingress & Edge Routing | Caddy reverse proxy, Cloudflare tunnel routing, and internal port blocking | [LOCKED] |
| **Phase 18** | Security Hardening Audit | Adversarial verification of SQLi, IDOR, brute force, headers, and secret leaks | [LOCKED] |
| **Phase 19** | Reliability & Chaos Testing | Chaos runbook: container kills, network disconnects, daemon crashes, graceful restart | [LOCKED] |
| **Phase 20** | Performance & Quota Testing | 100-project burst load test (1,410 requests, 84.5 ms p50, 0 errors, 256 MB cap) | [LOCKED] |
| **Phase 21** | External App E2E Verification | Standalone `TaskManager` CLI app validating full workflow via `homelab-sdk` | [LOCKED] |
| **Phase 22** | Integration Sprint & Bug Fixes | Backup/restore state tracking fixes and schema synchronization hardening | [LOCKED] |
| **Phase 23** | Production Readiness Hardening | Dependency audit, code cleanup, strict memory limits, and logging redaction | [LOCKED] |
| **Phase 24** | Product Documentation | Complete developer guides, API references, security guides, and deployment docs | [LOCKED] |
| **Phase 25** | Final Release Verification | Final comprehensive release verification gate and permanent artifact lock | [LOCKED] |

---

## Deployment & Getting Started

### Prerequisites

- **Host OS:** Linux (Ubuntu 22.04+ recommended) or Windows with WSL2 / Docker Desktop
- **Hardware:** Minimum 1 Core CPU, 1 GB available RAM (Optimized for 4 GB RAM total system memory)
- **Software:** Docker (v20.10+) and Docker Compose (v2.0+)

---

### Local Installation & Startup

```bash
# 1. Clone the repository
git clone https://github.com/sharancode3/Homelab.git
cd Homelab

# 2. Build the Dashboard Frontend Assets
cd auth-service/dashboard
npm install
npm run build
cd ../..

# 3. Configure Environment Variables
cp core/.env.example core/.env
# Edit core/.env and set your PLATFORM_SECRET_KEY and domain configurations

# 4. Start the Entire Platform Stack
cd core
docker compose up -d --build

# 5. Verify Running Containers
docker compose ps
```

---

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PLATFORM_ENVIRONMENT` | `production` | Deployment mode (`development`, `staging`, `production`) |
| `PLATFORM_DEBUG` | `false` | Enable verbose debug logging |
| `PLATFORM_API_HOST` | `0.0.0.0` | Bind host for FastAPI backend |
| `PLATFORM_API_PORT` | `8000` | Internal bind port for FastAPI |
| `PLATFORM_STORAGE_PATH` | `/var/lib/auth-service/data` | Persistent host volume path for all tenant databases and blobs |
| `PLATFORM_SECRET_KEY` | *(Required in Production)* | Cryptographic secret key for HS256 JWT signing and internal tokens |
| `CORS_ALLOWED_ORIGINS` | `*` | Comma-separated list of permitted browser origins |

---

### Health and Readiness Verification

Verify the system is running and reporting healthy state:

```bash
# Check platform readiness
curl -s http://localhost/health

# Inspect detailed system & disk health metrics
curl -s http://localhost/api/v1/health/platform
```

Expected JSON Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "sqlite_latency_ms": 1.42,
    "disk_free_mb": 24580,
    "disk_status": "OK"
  }
}
```

---

## Security Invariants & Compliance

1. **No Plaintext Secrets:** Passwords are consistently hashed using Argon2id with automatic salt generation. Raw API keys (`pk_live_***`) are generated once and only stored as SHA-256 digests.
2. **Explicit Cryptographic Algorithm:** JWT tokens strictly enforce `HS256`. Asymmetric fallback and none-algorithm bypasses are strictly prevented by PyJWT validation settings.
3. **Audience Segregation:** Management tokens (`aud="developer"`) cannot be utilized against end-user endpoints, and end-user tokens (`aud="end_user"`) cannot access developer or project administration APIs.
4. **Host Port Protection:** Internal database, cache, and backend ports are never exposed to the public network. Public ingress is mediated entirely by Caddy and Cloudflare Zero Trust.
5. **Memory Constraint Guarantee:** The Platform Orchestrator process is locked to a maximum memory ceiling of `256M` in `docker-compose.yml`, preventing memory exhaustion or host destabilization.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

