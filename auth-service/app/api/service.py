from app.api.models import (
    BackupRequest,
    DeployRequest,
    HealthResponse,
    OperationResponse,
    OperationHistoryEntry,
    OperationHistoryResponse,
    ProjectMetricsResponse,
    ProjectStatusResponse,
    PlatformMetricsResponse,
    ProjectRegisterRequest,
    ProjectRegisterResponse,
    RestoreRequest,
    StopRequest,
    RestartRequest,
    LogsResponse,
    LogEventResponse,
    ValidateResponse,
)
from app.storage.interfaces import OperationHistoryRepository
from app.platform.health.engine import HealthEngine
from app.platform.audit.engine import AuditEngine
from app.platform.lifecycle.manager import LifecycleManager
from app.platform.operations.coordinator import PlatformOperationsCoordinator
from app.platform.operations.enums import OperationType
from app.platform.validation.engine import ValidationEngine
from app.project_registry import ProjectRegistryEntry, ProjectStatus, ProjectType
from app.project_registry_manager import ProjectRegistryManager
from app.observability.tracing import trace_scope
from app.observability.models import TraceContext
from app.security.hardening.validation import InputValidator


class APIServiceLayer:
    """Service layer decoupling FastAPI routes from platform internals."""

    def __init__(
        self,
        registry: ProjectRegistryManager,
        lifecycle: LifecycleManager,
        validation: ValidationEngine,
        health: HealthEngine,
        coordinator: PlatformOperationsCoordinator,
        audit_engine: AuditEngine = None,
        history_repository: OperationHistoryRepository = None,
        storage_path: str = None,
    ) -> None:
        self._registry = registry
        self._lifecycle = lifecycle
        self._validation = validation
        self._health = health
        self._coordinator = coordinator
        self._audit_engine = audit_engine
        self._history_repository = history_repository
        self._storage_path = storage_path

    def register_project(self, req: ProjectRegisterRequest) -> ProjectRegisterResponse:
        InputValidator.validate_payload(req.model_dump() if hasattr(req, "model_dump") else req.dict())
        try:
            ptype = ProjectType(req.project_type)
        except ValueError:
            ptype = ProjectType.BACKEND

        entry = ProjectRegistryEntry(
            project_id=req.project_id,
            project_name=req.project_name,
            project_slug=req.project_slug,
            project_type=ptype,
            status=ProjectStatus.ACTIVE,
            project_version=req.project_version,
        )
        self._registry.register(entry)

        from app.platform.lifecycle.exceptions import LifecycleConflictError
        try:
            self._lifecycle.register(req.project_id)
        except LifecycleConflictError:
            pass

        return ProjectRegisterResponse(
            project_id=req.project_id,
            status="success",
            message="Project registered successfully",
        )

    def validate_project(self, project_id: str) -> ValidateResponse:
        from app.platform.lifecycle.exceptions import LifecycleConflictError
        try:
            self._lifecycle.validate(project_id)
        except LifecycleConflictError:
            pass

        res = self._validation.validate(project_id, "deploy")
        issues = [f"{i.code}: {i.message}" if hasattr(i, "code") else f"{i.category.value}: {i.message}" for i in res.issues]
        return ValidateResponse(
            project_id=project_id,
            is_valid=res.is_valid,
            issues=issues,
        )

    def deploy_project(self, project_id: str, req: DeployRequest) -> OperationResponse:
        InputValidator.validate_payload(req.model_dump() if hasattr(req, "model_dump") else req.dict())
        with trace_scope(TraceContext(correlation_id=req.correlation_id or "auto")):
            res = self._coordinator.execute_operation(
                project_id=project_id,
                operation_type=OperationType.DEPLOY,
                requested_by=req.requested_by,
                correlation_id=req.correlation_id,
                configuration=req.configuration,
            )
        return OperationResponse(
            operation_id=res.operation_id,
            status=res.status.value,
            completed_steps=list(res.completed_steps),
            failures=list(res.failures),
        )

    def backup_project(self, project_id: str, req: BackupRequest) -> OperationResponse:
        InputValidator.validate_payload(req.model_dump() if hasattr(req, "model_dump") else req.dict())
        with trace_scope(TraceContext(correlation_id=req.correlation_id or "auto")):
            res = self._coordinator.execute_operation(
                project_id=project_id,
                operation_type=OperationType.BACKUP,
                requested_by=req.requested_by,
                correlation_id=req.correlation_id,
                backup_type=req.backup_type,
            )
        return OperationResponse(
            operation_id=res.operation_id,
            status=res.status.value,
            completed_steps=list(res.completed_steps),
            failures=list(res.failures),
        )

    def restore_project(self, project_id: str, req: RestoreRequest) -> OperationResponse:
        InputValidator.validate_payload(req.model_dump() if hasattr(req, "model_dump") else req.dict())
        with trace_scope(TraceContext(correlation_id=req.correlation_id or "auto")):
            res = self._coordinator.execute_operation(
                project_id=project_id,
                operation_type=OperationType.RESTORE,
                requested_by=req.requested_by,
                correlation_id=req.correlation_id,
                backup_id=req.backup_id,
            )
        return OperationResponse(
            operation_id=res.operation_id,
            status=res.status.value,
            completed_steps=list(res.completed_steps),
            failures=list(res.failures),
        )

    def get_health(self, project_id: str) -> HealthResponse:
        res = self._health.evaluate(project_id)
        return HealthResponse(
            project_id=project_id,
            state=res.state.value,
            status=res.status.value,
            success=res.success,
            message=res.message,
        )

    def stop_project(self, project_id: str, req: StopRequest) -> OperationResponse:
        InputValidator.validate_payload(req.model_dump() if hasattr(req, "model_dump") else req.dict())
        with trace_scope(TraceContext(correlation_id=req.correlation_id or "auto")):
            res = self._coordinator.execute_operation(
                project_id=project_id,
                operation_type=OperationType.STOP,
                requested_by=req.requested_by,
                correlation_id=req.correlation_id,
            )
        return OperationResponse(
            operation_id=res.operation_id,
            status=res.status.value,
            completed_steps=list(res.completed_steps),
            failures=list(res.failures),
        )

    def restart_project(self, project_id: str, req: RestartRequest) -> OperationResponse:
        InputValidator.validate_payload(req.model_dump() if hasattr(req, "model_dump") else req.dict())
        with trace_scope(TraceContext(correlation_id=req.correlation_id or "auto")):
            res = self._coordinator.execute_operation(
                project_id=project_id,
                operation_type=OperationType.RESTART,
                requested_by=req.requested_by,
                correlation_id=req.correlation_id,
            )
        return OperationResponse(
            operation_id=res.operation_id,
            status=res.status.value,
            completed_steps=list(res.completed_steps),
            failures=list(res.failures),
        )

    def get_project_logs(self, project_id: str, limit: int = 100) -> LogsResponse:
        if not self._audit_engine:
            return LogsResponse(project_id=project_id, logs=[])

        records = self._audit_engine.query(project_id=project_id)
        # Sort by timestamp descending and apply limit
        records = sorted(records, key=lambda x: x.timestamp, reverse=True)[:limit]

        logs = []
        for r in records:
            logs.append(LogEventResponse(
                audit_id=r.audit_id,
                timestamp=r.timestamp.isoformat(),
                event_type=r.event_type,
                severity=r.severity.value,
                message=r.summary,
            ))

        return LogsResponse(project_id=project_id, logs=logs)

    # ─── Phase 14.4 Monitoring ─────────────────────────────────────────────────

    def get_project_status(self, project_id: str) -> ProjectStatusResponse:
        """Return the current lifecycle state. Deployment handle is in-process
        only (DockerDeploymentProvider), so deployment_status is always marked
        as simulated until a persistent runtime exists."""
        state_map = getattr(self._lifecycle, "_states", {})
        lifecycle_state = state_map.get(project_id)
        if lifecycle_state is None:
            lifecycle_state_str = "unknown"
        else:
            lifecycle_state_str = lifecycle_state.value
        return ProjectStatusResponse(
            project_id=project_id,
            lifecycle_state=lifecycle_state_str,
            deployment_status="unknown",
            simulated=True,
            message="Deployment handle tracking is in-process only. Status reflects lifecycle state.",
        )

    def get_project_history(
        self, project_id: str, limit: int = 100
    ) -> OperationHistoryResponse:
        """Retrieve operation history for a project, bounded by limit (max 500)."""
        if not self._history_repository:
            return OperationHistoryResponse(
                project_id=project_id, total_returned=0, history=[]
            )
        limit = min(limit, 500)
        results = self._history_repository.get_history(
            project_id=project_id, limit=limit
        )
        history = [
            OperationHistoryEntry(
                operation_id=r.operation_id,
                status=r.status.value,
                completed_steps=list(r.completed_steps),
                failures=list(r.failures),
            )
            for r in results
        ]
        return OperationHistoryResponse(
            project_id=project_id,
            total_returned=len(history),
            history=history,
        )

    def get_project_metrics(self, project_id: str) -> ProjectMetricsResponse:
        """Return process-global operation counters, clearly labeled since_restart.
        Counters are not per-project but reflect all operations since last restart."""
        from app.observability.metrics import default_registry
        return ProjectMetricsResponse(
            project_id=project_id,
            since_restart=True,
            operation_success_count=default_registry.get_counter("operation_success_count"),
            operation_failure_count=default_registry.get_counter("operation_failure_count"),
            deployment_failures=default_registry.get_counter("deployment_failures"),
            backup_success_count=default_registry.get_counter("backup_success_count"),
            avg_operation_duration_ms=round(
                default_registry.get_average_duration("operation_deploy_duration") * 1000, 3
            ),
        )

    def get_platform_metrics(self) -> PlatformMetricsResponse:
        """Return real host CPU/RAM/disk metrics via psutil plus in-memory counters."""
        from datetime import datetime, timezone
        import psutil
        from app.observability.metrics import default_registry

        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        storage_target = str(self._storage_path) if self._storage_path else "."
        disk = psutil.disk_usage(storage_target)

        avg_durations = {
            k: round(sum(v) / len(v) * 1000, 3)
            for k, v in default_registry.durations.items()
            if v
        }

        return PlatformMetricsResponse(
            cpu_percent=cpu,
            memory_total_mb=round(mem.total / 1024 / 1024, 2),
            memory_available_mb=round(mem.available / 1024 / 1024, 2),
            memory_used_percent=mem.percent,
            disk_total_mb=round(disk.total / 1024 / 1024, 2),
            disk_used_mb=round(disk.used / 1024 / 1024, 2),
            disk_used_percent=disk.percent,
            since_restart_counters=dict(default_registry.counters),
            since_restart_avg_durations_ms=avg_durations,
            collected_at=datetime.now(timezone.utc).isoformat(),
        )
