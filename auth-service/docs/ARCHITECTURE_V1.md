# Architecture V1: Platform Orchestrator Constitution

This document serves as the fundamental architecture constitution for the Platform Orchestrator system following the completion of Phase 9A and Phase 10. It defines the core responsibilities, boundaries, and rules that govern the platform.

## 1. Core Philosophy
The platform is built on a modular orchestration system where workflows, infrastructure, security, and operations are strictly separated. 
- **Engines own workflows, not infrastructure.**
- **Adapters own infrastructure, not workflows.**
- **Coordinators own orchestration, not business logic.**

---

## 2. Phase 9A Architecture (The Brain)
Phase 9A established the internal workflow processing logic of the platform.

### Engine Responsibilities
No engine is permitted to become a "god class". Each engine is narrowly scoped:
- **Lifecycle Manager**: Owns the state machine and valid transitions for a project.
- **Validation Engine**: Owns readiness and compliance decisions before operations execute.
- **Deployment Engine**: Owns the workflow of deploying, pausing, resuming, and rolling back.
- **Backup Engine**: Owns the workflow of safely capturing system state and data.
- **Restore Engine**: Owns the workflow of reverting the system to a previous backup state.
- **Health Engine**: Owns continuous evaluation of running services.
- **Event Engine**: Owns the coordination of asynchronous events across the platform.
- **Audit Engine**: Owns the immutable, append-only historical record of operations.

### Platform Operations Coordinator
The Coordinator serves as the central dispatcher. It translates high-level requests (e.g., "Deploy Project X") into the specific sequence of engine invocations (Validate -> Backup -> Deploy -> Audit). It does not contain its own business logic.

---

## 3. Phase 10 Architecture (The Body)
Phase 10 wrapped the internal brain with external services, forming a deployable production platform.

### Architecture Map
```text
                    Users / Clients
                          |
                    FastAPI API Layer
                          |
                 Security + Validation
                          |
              Platform Operations Coordinator
                          |
        ------------------------------------------------
        |        |        |        |        |          |
   Lifecycle Validation Deployment Backup Restore Health
                          |
        ------------------------------------------------
        |                  |                 |
   Persistence        Adapters          Observability
        |                  |                 |
    SQLite DB        Providers          Metrics/Logs
                          |
        ------------------------------------------------
        |                  |
 Deployment Provider   Storage Provider
        |
 Docker Runtime
```

### Dependency Rules
- **API Boundary**: The API translates external requests into internal DTOs. Engines NEVER parse HTTP requests or return HTTP responses.
- **Security Boundary**: Authentication answers "Who are you?". Authorization answers "What can you do?". Security operates *before* the coordinator executes. Engines trust the `IdentityContext` provided to them.
- **Observability Layer**: Telemetry (logs, metrics, tracing) observes the platform passively via `contextvars`. It does not influence control flow.
- **Reliability Layer**: Retries, recovery, and Dead Letter Queues wrap operations from the outside. Transient errors are retried; fatal errors are halted.

### Adapter Rules
Adapters are the most critical boundary protecting the platform from infrastructure churn.
- **Engines depend on Adapter Contracts (Interfaces).**
- **Providers implement the Adapter Contracts.**
- **Engines DO NOT import Providers.** 
*(e.g. `DeploymentEngine` talks to `DeploymentAdapter`, not `DockerDeploymentProvider`)*

### Repository Rules
- Persistence is abstracted via the Repository Pattern.
- Engines depend on Repositories, which in turn map to underlying storage (currently SQLite).
- Repositories handle all ORM logic; engines only deal with pure domain objects.

---

## 4. Future Roadmap: Phase 11 (Real Infrastructure Integration)
Phase 10 created the stable skeleton. Phase 11 will integrate production-grade external infrastructure by swapping out the Phase 10 adapters.

1. **Real Database**: Replace SQLite with PostgreSQL (Migrations, Connection Pooling, Transactions).
2. **Real Authentication Provider**: Connect Auth Service to standard JWT/OAuth.
3. **Real Event Broker**: Replace in-memory transport with Redis Streams, RabbitMQ, or Kafka.
4. **Real Deployment Execution**: Upgrade the simulated Docker adapter to a real Docker API implementation.
5. **Cloud Storage**: Replace Local Storage with S3-compatible blob storage.
6. **Kubernetes Support**: Introduce a `KubernetesDeploymentProvider` alongside Docker.
7. **Monitoring Stack**: Integrate Prometheus, Grafana, and OpenTelemetry.

---
**Guiding Principle for the Future:** As we migrate to Phase 11, the core Phase 9A workflow engines must remain untouched. We will only change the providers injected into the adapters.
