# Homelab / BaaS — Master 25-Phase Roadmap

> **STATUS: ROADMAP CONTROL DOCUMENT**
>
> This file is the project-level source of truth for roadmap sequencing and scope. It exists to prevent phase drift, invented features, skipped phases, accidental resequencing, and pulling later-phase functionality into an earlier phase.
>
> **Critical rule:** A phase may not be implemented from assumptions about what a "typical" BaaS should contain. The exact phase definition in this document must be used for preflight, implementation planning, execution, verification, and lock/commit decisions.

---

## 0. Non-Negotiable Roadmap Workflow

Every phase follows this exact pipeline:

1. **Roadmap definition** — confirm the exact phase and sub-phase scope.
2. **Read-only preflight** — inspect the repository against that definition only.
3. **Gap analysis** — separate already-implemented functionality from genuine gaps.
4. **Boundary audit** — identify anything that would pull functionality from later phases.
5. **Open decisions** — resolve architecture/security/scope decisions before implementation planning.
6. **Implementation plan** — produce an explicit file/component/test plan.
7. **Plan approval** — no implementation before approval.
8. **Implementation** — implement only the approved scope.
9. **Verification** — unit/integration/security tests, smoke tests, and diff checks as applicable.
10. **Review/fixes** — resolve failures before locking.
11. **Commit + push** — only after verification is green.
12. **Checkpoint lock** — record commit hash and working-tree state.
13. **Next phase preflight** — only after the previous phase is locked.

### Absolute scope rules

- Never invent a missing roadmap phase.
- Never infer a phase definition from `ARCHITECTURE_V1.md` when the master roadmap says otherwise.
- Never merge two phases because functionality appears related.
- Never skip a phase because its functionality already partially exists; instead, document what was pulled forward and implement only the remaining scope.
- Never pull Phase N+1/N+2 functionality into Phase N for convenience.
- Existing functionality may satisfy part of a later phase, but the later phase still needs a preflight against its exact definition.
- Security fixes required to protect the current phase are allowed; unrelated future architecture is not.
- Preserve existing security boundaries, tenant isolation, API contracts, and adapter/engine boundaries unless the approved phase explicitly changes them.

---

# 1–10 — Historical / Earlier Roadmap

**IMPORTANT:** The original exact definitions for Phases 1–10 were not recoverable from the current conversation context when this control document was created. The repository contains `docs/PHASE10_ROADMAP.md`, but that is an older Phase 10 conversion roadmap and is **not** to be treated as the 25-phase master roadmap.

Therefore these phases are intentionally **NOT reconstructed or guessed here**.

When the original master roadmap is recovered, replace this section with the exact original titles, sub-phases, scope, exclusions, and dependencies. Until then, do not use assumptions about Phases 1–10 to justify new implementation work.

---

# 11 — BaaS Foundation / Developer Platform

## 11.1 — Developer Identity / Authentication

**Status:** LOCKED

Establish the developer identity/authentication foundation used by the BaaS control plane.

## 11.2 — Projects + Ownership + Security Boundary

**Status:** LOCKED — `3908b13`

Establish projects, ownership, project isolation, and the fundamental security boundary between projects and developer identities.

## 11.3 — Team Membership + RBAC

**Status:** LOCKED — `b3d41f6`

Establish project team membership and the four project roles:

- Owner
- Admin
- Developer
- Viewer

Provide role-aware authorization guards and enforce owner invariants, including last-owner protection and prevention of unauthorized owner promotion.

## 11.4 — Project API Keys

**Status:** LOCKED — `28cd995`

Provide project-scoped API key generation, storage/hash handling, listing, revocation/rotation, and IDOR protection.

API keys form the project Data Plane authentication mechanism.

## 11.5 — Database / Tables / Data Service Foundation

**Status:** LOCKED — `a2c2700`

Establish isolated per-project SQLite databases, table management, basic CRUD, pagination, identifier validation, and Data Plane access through project API keys.

## 11.6 — Team Collaboration

**Status:** LOCKED — `5fb81c0`

Complete HTTP-layer RBAC verification for team collaboration and validate role enforcement end-to-end through FastAPI dependency wiring.

Scope includes developer/viewer permissions, member management restrictions, non-member rejection, authentication failures, owner invariants, and member removal/access revocation.

---

# 12 — Developer API + SDK / Public BaaS API

**Status:** LOCKED — `77dccb1`

Expose and harden the public developer-facing BaaS API foundation.

Confirmed scope implemented:

- Developer API authentication flow.
- API-key and JWT authorization boundaries.
- Public API contract corrections.
- `POST` resource creation responses using HTTP `201 Created` where required.
- Developer auth refresh endpoint.
- CORS middleware with environment-controlled configuration.
- Platform health endpoint.
- Existing platform operations exposed only with appropriate RBAC.
- API-key/Data Plane and developer/control-plane boundaries preserved.

### Explicit boundary

Rate limiting is **not** part of Phase 12 itself. It is Phase 12.5.

---

# 12.5 — Rate Limiting

**Status:** LOCKED — `9ac43dc`

Implement bounded in-memory Token Bucket rate limiting appropriate for the single-node SQLite architecture.

Confirmed scope:

- Token Bucket implementation.
- Bounded/LRU in-memory bucket storage.
- Control Plane rate limiting keyed by client IP.
- Data Plane rate limiting keyed by project API key.
- `429 Too Many Requests` enforcement.
- `Retry-After` behavior.
- Correct time-based refill/recovery.
- HTTP/unit verification and live smoke verification.

### Explicit boundary

No distributed Redis rate limiter or other Phase 17+ production infrastructure is introduced here.

---

# 13 — Database / Data Service

**Status:** LOCKED — `99c7535`

Extend the Phase 11.5 database foundation into the planned BaaS database/data-service capabilities without duplicating already-implemented CRUD foundations.

Confirmed Phase 13 implementation scope included:

- Schema alteration support through `ALTER TABLE ... ADD COLUMN`.
- Strict identifier validation for schema changes.
- Secure tenant-isolated schema modification.
- Database security and SQL-injection validation.
- Reserved SQLite/internal identifier protection.
- Security testing of malicious identifiers and payloads.

### Explicit boundary

Do not pull later-phase relationships, advanced indexing, performance systems, or unrelated infrastructure into this phase unless the exact master roadmap definition explicitly assigns them here.

---

# 14 — BaaS Application Services

Phase 14 is split into four locked sub-phases.

## 14.1 — Developer Authentication Service / End-User Auth

**Status:** LOCKED — `33e4e48`

Provide project-scoped end-user authentication while maintaining a cryptographic boundary from developer authentication.

Confirmed scope:

- End-user registration/login/refresh.
- Email verification.
- Password reset.
- End-user `/me` access.
- Explicit JWT `aud="end_user"`.
- Developer JWTs use `aud="developer"`.
- Project-bound `project_id` claim.
- Strict cross-project rejection.
- Isolated `_baas_auth_users` tenant storage.
- Injectable email provider with mock provider for tests.
- Secure verification/reset token generation, hashing, expiry, single-use behavior, and enumeration-safe reset flow.

## 14.2 — Storage Service

**Status:** LOCKED — `1ed2410`

Provide static project-scoped file storage.

Confirmed scope:

- Upload.
- Download.
- List metadata.
- Delete.
- Tenant/project isolation.
- Path traversal protection.
- 5 MB maximum file size.
- 100 MB project storage quota.
- Streaming I/O.
- File metadata persisted in tenant SQLite storage.
- Checksum handling.
- API-key/developer/end-user authorization according to the locked access matrix.
- Backup manifest integration for storage artifacts.

### Explicit exclusions

- Static site hosting.
- CDN.
- Edge caching.
- Media transformation.

These are not to be pulled into 14.2.

## 14.3 — Deployment Integration

**Status:** LOCKED — `874a107`

Expose the existing Phase 10.5 platform operation engines through the BaaS Developer API.

Confirmed scope:

- Deploy.
- Stop.
- Restart.
- Health.
- Logs.
- Existing Backup/Restore operations where already provided by the platform layer.
- RBAC protection.
- Project isolation.
- Logs represented honestly using existing AuditEngine events because real container stdout does not yet exist.

### Explicit exclusions

- CPU/RAM metrics.
- Prometheus.
- Grafana.
- Real-time observability dashboards.
- Advanced monitoring systems.

Those belong to monitoring/later phases.

## 14.4 — Monitoring

**Status:** LOCKED — `feb33f3`

Provide monitoring/visibility appropriate to the simulated platform at this stage.

Confirmed scope:

- Project status endpoint.
- Project operation history endpoint.
- Project-scoped metrics visibility.
- Internal platform metrics endpoint.
- Real host CPU/RAM/disk metrics through `psutil`.
- Real database latency health checks.
- Storage-path health checks.
- History result hard cap of 500 records.
- In-process operation counters, clearly treated as volatile/process-global.
- Simulated deployment/container status explicitly represented as simulated rather than fabricated as real container telemetry.
- Strict RBAC and project isolation.

### Explicit exclusions

- Prometheus scrape format.
- Grafana.
- Alertmanager/alerting rules.
- SSE/WebSocket real-time metrics.
- Performance benchmarking.
- Monitoring dashboard UI.
- CDN/load-balancer/ingress metrics.

---

# 15 — Security + Reliability Audit

**Status:** LOCKED — `21e2e02`

Harden the existing system against identified security and reliability weaknesses while preserving the existing architecture and avoiding future-phase infrastructure.

Confirmed scope:

### Authentication security

- JWT `jti` issuance.
- Lightweight SQLite token revocation repository.
- Explicit logout/revocation.
- Revocation checks in developer and end-user authentication dependencies.
- Bounded pruning of expired revocation records.
- Preservation of `aud` and `project_id` security boundaries.
- Email enumeration protection.

### Resource/exhaustion safeguards

- Maximum 50 tables per project.
- Maximum 50 columns per table.
- Maximum identifier length of 64 characters.
- Preserve established payload/pagination contracts.
- Preserve the Phase 14.2 5 MB file limit and 100 MB project quota.
- Streamed storage-size enforcement independent of falsified `Content-Length` headers.
- Filename sanitization/path traversal protection.

### Reliability safeguards

- Controlled SQLite `OperationalError` handling.
- Controlled filesystem `OSError` handling.
- Safe `503 Service Unavailable` responses where appropriate.
- Bounded synchronous email failure handling without background queues.
- No Redis, broker, or worker infrastructure introduced for this audit.

### Explicit exclusions

- Phase 16 dashboard work.
- Phase 17 production/container infrastructure.
- Phase 18 full platform hardening such as mTLS/fail2ban/signing-key rotation.
- Phase 19 deliberate failure campaigns.
- Phase 20 performance/advanced quota systems.

---

# 16 — Dashboard / Developer-Facing Monitoring UI

**Current status:** NEXT PHASE — NOT STARTED

The available locked roadmap references establish Phase 16 as the **Dashboard** phase. The exact original 16.1+ sub-phase definitions are **not currently recoverable** from the original master roadmap.

### Confirmed boundary

Phase 16 must not be started from assumptions. Before implementation:

1. Recover the exact Phase 16.1+ definitions.
2. Perform a read-only preflight against those definitions.
3. Identify what Phase 14.4 already provides that the dashboard can consume.
4. Explicitly exclude Phase 17+ functionality.
5. Create and approve an implementation plan.

### Known exclusion from prior locked planning

Phase 16 is the developer-facing dashboard/UI layer. It must not become a reason to introduce production deployment infrastructure, real container telemetry, CDN/ingress infrastructure, or performance systems prematurely.

---

# 17 — Public Production / Real Runtime Infrastructure

**Known title/scope reference — NOT YET FULLY RECOVERED**

Prior locked planning identifies Phase 17 as the **Public Prod** phase.

Confirmed future-boundary examples from earlier planning:

- Real production/container constraints.
- Docker/cgroup resource constraints.
- Production filesystem restrictions.
- Real public runtime infrastructure.

The exact original 17.x sub-phases must be recovered before Phase 17 preflight. Do not infer the remaining details.

---

# 18 — Full Platform Hardening

**Known title/scope reference — NOT YET FULLY RECOVERED**

Prior locked planning identifies Phase 18 as **Full Hardening**.

Examples explicitly deferred to this phase in the Phase 15 plan include:

- Strict mTLS.
- fail2ban/IP blocking.
- JWT signing-key rotation.
- Broader production security perimeter hardening.

The exact original 18.x sub-phases must be recovered before Phase 18 preflight.

---

# 19 — Deliberate Failure / Failure Campaign

**Known title/scope reference — NOT YET FULLY RECOVERED**

Prior locked planning identifies Phase 19 as the **Failure Campaign** phase.

Examples explicitly deferred to this phase include deliberate simulation/testing of:

- Network partitions.
- Disk-full conditions.
- SMTP/email-provider outages.
- Other controlled infrastructure failure scenarios.

The exact original 19.x sub-phases must be recovered before Phase 19 preflight.

---

# 20 — Performance / Advanced Quotas

**Known title/scope reference — NOT YET FULLY RECOVERED**

Prior locked planning identifies Phase 20 as the **Performance/Quotas** phase.

Examples explicitly deferred to this phase include:

- Dynamic quota tracking.
- Advanced usage measurement.
- Concurrent load testing.
- Performance benchmarking.
- Per-project performance/throughput analysis.

The exact original 20.x sub-phases must be recovered before Phase 20 preflight.

---

# 21–25 — Later Roadmap

The exact original definitions for Phases 21–25 are not currently recoverable from the available project/context material.

**Do not invent these phases.** They remain intentionally unresolved until the original master roadmap is recovered.

When recovered, each phase must be added with:

- Exact title.
- Exact sub-phase numbering.
- Goals.
- Included functionality.
- Explicit exclusions.
- Dependencies on earlier phases.
- Security boundaries.
- Infrastructure constraints.
- Verification requirements.

---

# Locked Checkpoint Ledger

| Phase | Status | Locked Commit |
|---|---|---|
| 11.1 Developer Identity/Auth | LOCKED | — |
| 11.2 Projects + Ownership | LOCKED | `3908b13` |
| 11.3 Team Membership + RBAC | LOCKED | `b3d41f6` |
| 11.4 Project API Keys | LOCKED | `28cd995` |
| 11.5 Database / Tables / Data | LOCKED | `a2c2700` |
| 11.6 Team Collaboration | LOCKED | `5fb81c0` |
| 12 Developer API | LOCKED | `77dccb1` |
| 12.5 Rate Limiting | LOCKED | `9ac43dc` |
| 13 Database / Data Service | LOCKED | `99c7535` |
| 14.1 End-User Auth | LOCKED | `33e4e48` |
| 14.2 Storage Service | LOCKED | `1ed2410` |
| 14.3 Deployment Integration | LOCKED | `874a107` |
| 14.4 Monitoring | LOCKED | `feb33f3` |
| 15 Security + Reliability Audit | LOCKED | `21e2e02` |
| 16 Dashboard | NEXT / NOT STARTED | — |
| 17 Public Prod | NOT STARTED | — |
| 18 Full Hardening | NOT STARTED | — |
| 19 Failure Campaign | NOT STARTED | — |
| 20 Performance / Quotas | NOT STARTED | — |
| 21 | UNRECOVERED | — |
| 22 | UNRECOVERED | — |
| 23 | UNRECOVERED | — |
| 24 | UNRECOVERED | — |
| 25 | UNRECOVERED | — |

---

# Current Project State

**Current locked phase:** Phase 15

**Current commit:** `21e2e02`

**Next phase:** Phase 16 — Dashboard

**Current rule:** Do not implement Phase 16 until the exact Phase 16 definition is recovered or explicitly re-established and approved.

---

# Roadmap Integrity Rule

This document is intentionally conservative. Where the original master roadmap is known, it records the scope and boundaries. Where it is not known, it explicitly says **UNRECOVERED** instead of manufacturing a plausible roadmap.

The project must never treat a guessed phase as the master roadmap.

If the original roadmap is later recovered, update this file first, review the changes, and only then resume phase execution.
