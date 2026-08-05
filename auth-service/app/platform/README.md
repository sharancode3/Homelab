# Platform Architecture

This is the central orchestration and management platform, containing decoupled engines that handle the full lifecycle of projects. 

## Engines and Responsibilities

- **Platform Operations Coordinator**: The central orchestration layer. It delegates high-level operations (like deploy, restart, backup) to the appropriate engine, while generating events and audit records.
- **Lifecycle Engine**: Manages state transitions and defines the current lifecycle state of projects (e.g., STARTED, STOPPED).
- **Validation Engine**: Read-only business rule evaluator that ensures operations are safe to execute given the current state of a project.
- **Deployment Engine**: Uses the validation engine to determine deployability, generates deployment plans, but delegates execution to infrastructure layers.
- **Backup Engine**: Coordinates the creation of backup plans and immutable manifest generation.
- **Restore Engine**: Validates target environments and compatibility, creates restore plans, and validates integrity of backup manifests.
- **Health Engine**: A read-only evaluation layer that resolves and aggregates project health statuses without side-effects.
- **Event Engine**: A deterministic publish/route/record layer for loose coupling and communication between components.
- **Audit Engine**: An append-only immutable recording layer providing a queryable and tamper-evident history of platform operations.

## Key Design Principles
- **No God Classes**: The coordinator orchestrates but contains no business logic or deployment code.
- **Read-Only / Side-Effect Free Layers**: Health and Validation engines are read-only to ensure predictable execution.
- **Immutable Results**: Engines output immutable result models rather than altering shared global state.
- **Strict Boundaries**: Each engine owns its domain. Events are routed by the Event Engine, and audits are recorded exclusively by the Audit Engine.
