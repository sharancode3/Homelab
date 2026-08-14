from app.api.models import (
    BackupRequest,
    DeployRequest,
    HealthResponse,
    OperationResponse,
    ProjectRegisterRequest,
    ProjectRegisterResponse,
    RestoreRequest,
    StopRequest,
    RestartRequest,
    LogsResponse,
    LogEventResponse,
    ValidateResponse,
)
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
    ) -> None:
        self._registry = registry
        self._lifecycle = lifecycle
        self._validation = validation
        self._health = health
        self._coordinator = coordinator
        self._audit_engine = audit_engine

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
