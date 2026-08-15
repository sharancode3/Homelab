# Homelab / BaaS — Master 25-Phase Roadmap

> **ROADMAP CONTROL DOCUMENT — SOURCE OF TRUTH**
>
> This document is the permanent roadmap reference for the project. It must be consulted before every phase preflight, implementation plan, implementation, verification, and lock. The purpose is to prevent scope drift, skipped work, invented features, accidental phase reordering, and later-phase functionality bleeding into an earlier phase.
>
> The roadmap below is based on the approved master roadmap supplied for this project. Where phase numbers have already been deliberately regrouped during execution, the original capability must still be preserved and mapped into the execution backlog rather than silently dropped.

---

# 0. Non-Negotiable Engineering Workflow

The project does **not** consider a phase complete merely because an agent generated code.

Every phase follows:

**Roadmap definition → Read-only preflight → Gap analysis → Boundary audit → Open decisions → Implementation plan → Explicit approval → Implementation → Tests → Review → Real verification → Fixes → Final verification → Commit + push → Locked checkpoint → Next-phase preflight**

## Mandatory rules

1. Confirm the exact phase and sub-phase definition before doing work.
2. Preflight must be read-only.
3. Do not infer missing scope from general BaaS conventions.
4. Identify what already exists before proposing changes.
5. Separate genuine gaps from already-satisfied requirements.
6. Explicitly identify Phase N+1/N+2 bleed risks.
7. Resolve important architecture/security/scope decisions before implementation.
8. No implementation before the implementation plan is approved.
9. Implement only the approved scope.
10. Every meaningful security or reliability fix requires verification.
11. Do not replace real verification with assumptions or mocked success when real verification is available.
12. Fix failures before declaring the phase complete.
13. Run regression verification so earlier phases remain intact.
14. Run smoke/integration verification where applicable.
15. `git diff --check` must be clean before lock.
16. Commit and push only after verification is green.
17. Record the exact commit hash and clean working-tree state.
18. Only then begin the next phase preflight.
19. **We do not skip verification to hit a date.**
20. At all times, prioritize security, tenant isolation, correctness, efficiency, and the 4 GB ThinkPad constraint.

## Architecture rules

- Do not casually change established engine boundaries.
- Prefer adapters/providers at infrastructure boundaries.
- Preserve API contracts unless the approved phase explicitly changes them.
- Preserve project isolation at every layer.
- Preserve explicit authentication → project → resource → operation authorization.
- Do not introduce heavy infrastructure merely because it is common in production BaaS systems.
- Redis, message brokers, Prometheus, Grafana, Kubernetes, external load balancers, and similar infrastructure must not appear early merely for convenience; introduce them only in the phase that explicitly requires them.
- When infrastructure is simulated, report it honestly as simulated rather than fabricating real telemetry.

---

# Roadmap Starting Point

- **Phase 9A:** Core Platform Engines — completed.
- **Phase 10:** Production Architecture — completed.
- **Phase 10.5:** Real Deployment Smoke Test — completed.
- **Next:** BaaS product conversion and verification.

The approved master roadmap originally grouped the capabilities broadly as:

- Phase 11 — BaaS Foundation
- Phase 12 — Developer API + SDK
- Phase 13 — Dashboard
- Phase 14 — Full BaaS Services
- Phase 15 — Security + Reliability Audit
- Phase 16 — Real External-App Integration
- Phase 17 — Production Deployment
- Phase 18 — Final Verification / Release 🔒 LOCKED

The phase numbers were explicitly allowed to be adjusted if the grouping was improved, provided the dependency/order remained essentially unchanged. Therefore the later execution numbering must be tracked carefully so that **no capability disappears merely because its phase number moved**.

---

# PHASE 11 — BaaS FOUNDATION

## Goal

Turn the existing platform into a **multi-user, multi-project BaaS**.

### 11.1 — User Account System

Build:

- User registration.
- Login.
- Logout.
- Password hashing.
- Sessions/access tokens.
- Account identity.
- User database.

Security requirements:

- Argon2id/bcrypt or an appropriately secure password hashing scheme.
- Never store plaintext passwords.
- Secure session/token handling.
- Input validation.
- Rate limiting on authentication endpoints.

Verification:

- Signup succeeds.
- Login succeeds.
- Wrong password is rejected.
- Unknown-user behavior is safe.
- Logout succeeds.
- Expired sessions are rejected.

### 11.2 — Email Verification

Flow:

`Signup → Verification email → User clicks link → Account verified`

Use a free transactional email provider initially, subject to its current free limits.

Security:

- Short-lived verification token.
- Hash token in database.
- Single-use token.
- Never expose token in logs.
- Resend verification.
- Prevent email enumeration.

Verification:

- Valid token → verified.
- Expired token → rejected.
- Used token → rejected.
- Modified token → rejected.

### 11.3 — Forgot Password / Reset Password

Flow:

`Forgot password → Enter email → Reset email → Secure reset link → New password → Old reset token invalidated`

Security:

- Cryptographically secure random token.
- Hashed token storage.
- Expiration.
- Single-use.
- Generic response regardless of account existence.
- Password re-hashing.
- Session invalidation after reset where appropriate.

Verification:

- Test the complete reset flow.
- Test expiry.
- Test replay.
- Test modified token.
- Test enumeration behavior.

### 11.4 — Multiple Projects Per User

Model:

`User → Project A / Project B / Project C`

Each project gets its own:

- Unique identity.
- Settings.
- Database.
- Storage.
- API keys.
- Members.
- Permissions.
- Deployment configuration.

Critical property:

**Project A must never access Project B.**

Verification:

- Create multiple projects.
- Aggressively test cross-project access.
- Test reads, writes, deletion, keys, storage, auth, and deployment boundaries.

### 11.5 — Project Ownership

Relationships:

- Users.
- Projects.
- Project members.

Every request must resolve:

`Identity → Project membership → Permission → Resource`

No layer may skip this chain.

### 11.6 — Team Collaboration

Project-specific members.

Initial roles:

- OWNER
- ADMIN
- DEVELOPER
- VIEWER

Permissions must be explicit rather than scattered throughout routes.

Verification:

- Test every role against every sensitive operation.
- Test non-members.
- Test owner invariants.
- Test removal and access revocation.

---

# PHASE 12 — API KEY + DEVELOPER API

Purpose: allow another developer's application to use the BaaS safely.

## 12.1 — Project API Keys

Flow:

`Create project → Generate key → Show once → Hash key → Store hash`

Example format:

`pk_live_xxxxxxxxx`

Never store the raw key.

Functions:

- Generate.
- List metadata.
- Revoke.
- Rotate.
- Optional expiration.
- Permission/scopes where defined by the API contract.

## 12.2 — API Authentication Middleware

External request:

`Authorization: Bearer pk_live_xxxxx`

Backend:

`API key → Hash → Find key → Find project → Check status → Check permissions → Allow request`

Every step must be project-scoped and fail closed.

## 12.3 — Public BaaS API

Define stable APIs for the product surface, including conceptual areas such as:

- `/v1/auth`
- `/v1/database`
- `/v1/storage`
- `/v1/projects`
- Other explicitly approved `/v1/...` resources.

Exact routes must be finalized before implementation rather than growing randomly.

## 12.4 — Authorization

Every request must answer:

`Who? → Which project? → Which resource? → Which operation? → Allowed?`

No endpoint may accidentally bypass this chain.

## 12.5 — Rate Limiting

Protect at minimum:

- Login.
- Signup.
- Password reset.
- API keys.
- Data APIs.
- File uploads.
- Expensive operations.

The 4 GB ThinkPad makes resource protection especially important.

The initial architecture should remain appropriate for a single-node environment; distributed rate limiting is not introduced merely for fashion.

---

# PHASE 13 — DATABASE / DATA SERVICE

This is a core part of the BaaS product: developers should be able to create tables and use them from their applications.

## 13.1 — Database Project Isolation

Each project requires an isolated data boundary.

Candidate architectures must be evaluated carefully for security and efficiency on the available hardware, e.g.:

`Project A → isolated schema/database`

`Project B → isolated schema/database`

The final architecture must be selected deliberately, not assumed.

## 13.2 — Table Management API

Users can:

- Create table.
- Delete table.
- List tables.
- Add column.
- Modify allowed schema properties.

## 13.3 — Data API

External applications can perform controlled:

- INSERT
- SELECT
- UPDATE
- DELETE

Conceptual flow:

`Application → API Key → BaaS API → Project authorization → Table authorization → Database`

## 13.4 — Dashboard Data Viewer

Project database view should expose tables such as:

- users
- products
- orders

Table viewer capabilities:

- Browse rows.
- Add row.
- Edit row.
- Delete row.
- Inspect columns.

## 13.5 — Database Security

Must prevent:

- SQL injection.
- Arbitrary SQL execution.
- Cross-project queries.
- Unauthorized table access.
- Malicious identifiers.
- Oversized queries.
- Resource exhaustion.

Verification:

Run deliberate attack/security tests.

---

# PHASE 14 — AUTH + STORAGE + EXISTING PLATFORM SERVICES

Expand the BaaS beyond database functionality.

## 14.1 — Developer Authentication Service

This is different from platform/admin authentication.

Conceptual flow:

`Developer App → BaaS Auth API → Their Project → Their Users`

Functions:

- Sign up.
- Sign in.
- Logout.
- Password reset.
- Email verification.
- Sessions/tokens.
- User management.
- Password changes.

Project A's users must never appear in Project B.

## 14.2 — Storage Service

Project storage example:

`Project → Storage → profile-images / documents / uploads`

Required capabilities:

- Upload.
- Download.
- Delete.
- Metadata.
- Project isolation.
- File-size limits.
- Content validation.
- Storage quotas.

The existing storage adapter/provider should be reused rather than replaced unnecessarily.

## 14.3 — Deployment Integration

Connect the BaaS product layer to the existing platform engines.

Required product operations:

- Deploy.
- Stop.
- Restart.
- Health.
- Logs.
- Backup.
- Restore.

## 14.4 — Monitoring

Expose appropriate visibility for:

- Health.
- CPU.
- RAM.
- Container status.
- Operation history.
- Deployment status.
- Failures.

Because the host is a 4 GB ThinkPad, resource visibility is important.

Monitoring must be honest about simulated infrastructure: do not fabricate container telemetry when no real container exists.

---

# PHASE 15 — SDK

Developers should not have to manually construct HTTP requests.

Start with a **Python SDK**.

Conceptual usage:

```python
from your_sdk import Client

client = Client(
    url="https://your-baas.example",
    api_key="pk_live_xxxxx"
)

client.auth.sign_up(...)
client.db.table("users").insert(...)
client.db.table("users").select(...)
client.storage.upload(...)
```

SDK should provide:

- Authentication.
- Database.
- Storage.
- Project APIs where appropriate.
- Error handling.
- Timeout handling.
- Retries where safe.
- Typed responses.

Later SDKs:

- JavaScript/TypeScript.
- Flutter.
- Android.

Do not build all SDKs at once.

### Execution alignment note

The project's phase numbering was deliberately regrouped during implementation. Security + Reliability was executed and locked as the current Phase 15. Therefore the **SDK requirement from this master roadmap is not considered deleted**. It remains a required capability and must be explicitly scheduled before the external-application milestone if it has not already been completed.

---

# PHASE 16 — DASHBOARD / FRONTEND

The frontend becomes meaningful because the backend product APIs exist.

Recommended initial stack:

- React.
- Vite.
- TypeScript.
- Tailwind.
- React Query.

## Dashboard structure

`Dashboard`

- Projects
- Selected Project
  - Overview
  - Database
    - Tables
    - Data
  - Authentication
  - Storage
  - API Keys
  - Deployments
  - Logs
  - Health
  - Team
  - Settings

## 16.1 — Account UI

- Login.
- Signup.
- Forgot password.
- Reset password.
- Verify email.
- Profile.

## 16.2 — Project UI

- Create project.
- Switch projects.
- Project settings.
- Delete project.

All project switching must preserve project isolation.

## 16.3 — Team UI

- Invite member.
- Change role.
- Remove member.

Role operations must use backend RBAC; frontend hiding alone is never a security control.

## 16.4 — Database UI

- Create table.
- Create columns.
- Browse data.
- Insert.
- Edit.
- Delete.

The UI must use the existing secured APIs rather than directly accessing databases.

## 16.5 — API Key UI

- Generate.
- Copy once.
- Revoke.
- Rotate.

Raw API keys must never be displayed again after the intended one-time reveal.

## 16.6 — Deployment UI

- Deploy.
- Status.
- Health.
- Logs.
- Backup.
- Restore.

### Phase 16 boundary

Do **not** turn the dashboard phase into production infrastructure. No CDN, public ingress, real production container orchestration, performance testing, or later-phase security campaign unless explicitly required by a reviewed roadmap change.

---

# PHASE 17 — FRONTEND DEPLOYMENT + PUBLIC ACCESS

Target architecture:

`INTERNET → Cloudflare → Frontend hosting / Backend API → Cloudflare Tunnel → ThinkPad`

ThinkPad-side services include the application/runtime, database, Docker, and storage as applicable.

The exact hosting arrangement must be confirmed before production deployment.

Critical rule:

**PostgreSQL must not be exposed directly to the public internet.**

Public access must be restricted through the intended gateway/tunnel/access-control architecture.

---

# PHASE 18 — FULL SECURITY HARDENING

Security is not postponed until Phase 18. Security is part of every previous phase.

Phase 18 is the **final adversarial security review**.

## Authentication security tests

- Brute force.
- Session expiry.
- Token replay.
- Reset-token replay.
- Email enumeration.
- Password policy.
- Credential leakage.

## API security tests

- Missing API key.
- Invalid API key.
- Revoked API key.
- Wrong project.
- Wrong role.
- Privilege escalation.
- IDOR.
- Malformed requests.
- Oversized payloads.
- Rate-limit bypass.

## Database security tests

- SQL injection.
- Cross-project queries.
- Unauthorized table access.
- Malicious identifiers.
- Resource exhaustion.

## Storage security tests

- Path traversal.
- Unauthorized downloads.
- Oversized uploads.
- Malicious filenames.
- Cross-project file access.

## Container security tests

- Non-root containers.
- Resource limits.
- Filesystem restrictions.
- Exposed ports.
- Environment secrets.
- Container-escape assumptions.

Phase 18 must be a review of the complete security perimeter, not an excuse to ignore security earlier.

---

# PHASE 19 — RELIABILITY + FAILURE TESTING 🔒 LOCKED

This phase deliberately breaks the system in controlled ways.

Failure scenarios include:

- Database unavailable.
- Docker unavailable.
- Network disappears.
- Container crashes.
- Storage write fails.
- Backup fails.
- Restore fails.
- Email provider unavailable.
- API key invalid.
- Process restarts.

For every controlled failure verify:

- Retry behavior where safe.
- Recovery.
- Audit trail.
- Correct error response.
- No corrupted state.

The reliability layer established earlier should be exercised here rather than merely inspected.

---

# PHASE 20 — PERFORMANCE + RESOURCE TESTING

The production hardware is a **ThinkPad with 4 GB RAM**, so actual measurements are required before establishing aggressive quotas.

Test progressively:

- 10 projects.
- 20 projects.
- 50 projects.
- 100 projects, only if the hardware can realistically sustain it.

Measure:

- RAM.
- CPU.
- Disk.
- Database size.
- API latency.
- Container count.
- Concurrent requests.

Then establish actual quotas based on measurements.

Examples of possible measured outcomes include:

- Container: 256 MB RAM.
- Container: 0.25 CPU.
- Database: measured MB quota.
- Storage: measured GB quota.

**Do not invent performance limits before measuring.**

---

# PHASE 21 — REAL EXTERNAL APPLICATION TEST

This is a major product milestone.

Use a completely separate external/test application.

Developer workflow:

`Create account`
→ `Verify email`
→ `Create project`
→ `Invite teammate`
→ `Generate API key`
→ `Install SDK`
→ `Connect application`
→ `Create table`
→ `Insert data`
→ `Read data`
→ `Update data`
→ `Authentication`
→ `Upload file`
→ `Deploy`
→ `Health`
→ `Backup`
→ `Restore`

Then open the dashboard and verify the same resources/data are visible there.

This phase proves that the BaaS works as an external product, not merely as an internal test suite.

---

# PHASE 22 — BUG-FIX / INTEGRATION SPRINT

This phase is deliberately separate from the external-app test.

For every discovered bug:

`Bug → Reproduce → Identify layer → Fix → Unit test → Integration test → Regression test`

No important bug receives a "quick patch" without a regression test.

The objective is to stabilize the complete integrated product after real-world use.

---

# PHASE 23 — PRODUCTION READINESS

## Code

- Remove debug code.
- Remove dead code.
- Type checking.
- Linting.
- Dependency audit.
- Environment configuration.

## Security

- Secrets outside repository.
- Production keys.
- HTTPS.
- Secure cookies/tokens.
- CORS.
- Rate limiting.
- Security headers.
- Logging redaction.

## Database

- Backups.
- Restore test.
- Migration strategy.
- Connection limits.
- Disk monitoring.

## Docker

- Non-root.
- Resource limits.
- Health checks.
- Restart policy.
- Image cleanup.

## Cloudflare / public access

- Tunnel.
- DNS.
- HTTPS.
- Access controls.
- No exposed internal services.

Every production boundary must be explicitly verified.

---

# PHASE 24 — DOCUMENTATION

Developer documentation must cover the complete product journey:

`Getting Started → Create Account → Create Project → Generate API Key → Install SDK → Connect Application`

Then document:

- Authentication API.
- Database API.
- Storage API.
- Deployment API.
- Backup API.
- SDK reference.
- Error codes.
- Security.
- Limits.

Internal documentation:

- Architecture.
- Database design.
- Deployment.
- Backups.
- Recovery.
- Security model.

Documentation must describe the real implemented behavior, not aspirational behavior.

---

# PHASE 25 — FINAL RELEASE VERIFICATION

This is the final gate.

## User management

- Signup ✅
- Login ✅
- Email verification ✅
- Forgot password ✅
- Reset password ✅
- Sessions ✅

## Projects

- Multiple projects ✅
- Project settings ✅
- Ownership ✅
- Team members ✅
- Roles ✅
- Isolation ✅

## BaaS

- Database ✅
- Tables ✅
- Data API ✅
- Authentication ✅
- Storage ✅
- API keys ✅
- SDK ✅

## Existing platform

- Deployment ✅
- Health ✅
- Backup ✅
- Restore ✅
- Audit ✅
- Reliability ✅
- Observability ✅

## Security

- Authentication ✅
- Authorization ✅
- Tenant isolation ✅
- API key security ✅
- Input validation ✅
- Rate limiting ✅
- Secrets protection ✅
- Database security ✅
- Storage security ✅
- Container security ✅

## Real-world proof

- External application ✅
- External developer ✅
- Team collaboration ✅
- Real deployment ✅
- Real database ✅
- Real storage ✅
- Real backup/restore ✅
- Failure recovery ✅

Only when the final gate is satisfied should the product be considered release-ready.

---

# Final Product Architecture Target

```text
                         YOUR BaaS
                            │
                     ┌──────┴──────┐
                     │             │
                  Website        SDK/API
                     │             │
                     └──────┬──────┘
                            │
                      Authentication
                            │
                         Projects
                            │
             ┌──────────────┼──────────────┐
             │              │              │
          Project A      Project B      Project C
             │              │              │
        ┌────┼────┐    ┌────┼────┐    ┌────┼────┐
        │    │    │    │    │    │    │    │    │
       DB   Auth Storage DB   Auth Storage DB   Auth Storage
        │
      Deploy
        │
      Backup
        │
      Health
        │
      Docker
        │
     ThinkPad
```

The finished product is a secure, multi-tenant developer platform in which the website and SDK/API access the same project-scoped services, while each project's DB, Auth, and Storage remain isolated.

---

# Execution Mapping / Current Locked State

The master roadmap allows phase numbers to be adjusted when grouping is improved, but capabilities cannot disappear.

Current locked execution history:

| Execution checkpoint | Capability | Commit | Status |
|---|---|---|---|
| 11.1 | Developer Identity/Auth | — | LOCKED |
| 11.2 | Projects + Ownership | `3908b13` | LOCKED |
| 11.3 | Team Membership + RBAC | `b3d41f6` | LOCKED |
| 11.4 | Project API Keys | `28cd995` | LOCKED |
| 11.5 | Database / Tables / Data | `a2c2700` | LOCKED |
| 11.6 | Team Collaboration | `5fb81c0` | LOCKED |
| 12 | Developer API | `77dccb1` | LOCKED |
| 12.5 | Rate Limiting | `9ac43dc` | LOCKED |
| 13 | Database / Data Service | `99c7535` | LOCKED |
| 14.1 | End-User Auth | `33e4e48` | LOCKED |
| 14.2 | Storage Service | `1ed2410` | LOCKED |
| 14.3 | Deployment Integration | `874a107` | LOCKED |
| 14.4 | Monitoring | `feb33f3` | LOCKED |
| 15 | Security + Reliability Audit | `21e2e02` | LOCKED |
| 16 | Dashboard / Frontend | `23715f3` | LOCKED |
| 17 | Advanced Routing & Production Ingress | `edae9ac` | LOCKED |

### Important capability bookkeeping

The original master roadmap placed the Python SDK in Phase 15. During execution, Phase 15 was deliberately used for the Security + Reliability Audit. Therefore the SDK is **not to be forgotten or considered complete merely because the phase number moved**. Before the Real External Application milestone, the SDK must either be implemented and verified or explicitly re-scoped by an approved roadmap decision.

Likewise, Phase 18 remains the final adversarial security review even though security safeguards were already implemented in the current Phase 15 execution. Earlier security work is foundational protection; Phase 18 is the final comprehensive review.

---

# Current Checkpoint

**Locked execution phase:** Phase 20 — PERFORMANCE + RESOURCE TESTING 🔒 LOCKED

**Locked commit:** `8740ce5`

**Next execution phase:** Phase 21 — REAL EXTERNAL APPLICATION TEST

**Phase 21 rule:** Do not implement from assumptions. Perform the normal read-only preflight → gap analysis → boundary audit → decisions → implementation plan → approval → implementation → verification pipeline.

---

# Roadmap Integrity Rule

The roadmap is not a suggestion.

For every future phase, the agent must first compare the requested work against this document and explicitly answer:

1. What exact roadmap item is being implemented?
2. What already exists?
3. What is genuinely missing?
4. What is explicitly excluded?
5. What later-phase functionality must **not** be introduced?
6. What security/tenant-isolation boundaries must remain intact?
7. What verification proves the phase is actually complete?

If the answer to any of these is unclear, stop at preflight and ask rather than guessing.

**Most important rule:** We do not skip verification to hit a date. The objective is not merely to finish code. The objective is to turn the existing Phase 9A/10 platform foundation into the secure, multi-tenant developer product envisioned by this roadmap and prove it with a real external application.
