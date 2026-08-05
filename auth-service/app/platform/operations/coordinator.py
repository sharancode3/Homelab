from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import Lock

from app.platform.audit.engine import AuditEngine
from app.platform.audit.enums import AuditCategory, AuditSeverity, AuditStatus
from app.platform.backup.engine import BackupEngine
from app.platform.backup.enums import BackupType
from app.platform.deployment.engine import DeploymentEngine
from app.platform.events.engine import EventEngine
from app.platform.events.enums import EventCategory, EventPriority
from app.platform.health.engine import HealthEngine
from app.platform.lifecycle.enums import LifecycleOperation
from app.platform.lifecycle.manager import LifecycleManager
from app.platform.operations.enums import OperationStatus, OperationType
from app.platform.operations.exceptions import (
    OperationConflictError,
    OperationException,
    OperationRequestError,
)
from app.platform.operations.models import OperationPlan, OperationResult
from app.platform.restore.engine import RestoreEngine
from app.platform.validation.engine import ValidationEngine
from app.observability.logger import StructuredLogger
from app.observability.metrics import default_registry
from app.observability.tracing import get_current_trace, trace_scope
from app.reliability.exceptions import RetryExhaustedError, NonRetryableError
from app.reliability.recovery import OperationRecoveryManager
from app.reliability.retry import RetryManager
from app.reliability.queue import EventReliabilityManager, DeadLetterQueue
from app.storage.interfaces import OperationHistoryRepository


class PlatformOperationsCoordinator:
    """Orchestration layer that coordinates operations across all platform engines."""

    def __init__(
        self,
        lifecycle_manager: LifecycleManager,
        validation_engine: ValidationEngine,
        deployment_engine: DeploymentEngine,
        backup_engine: BackupEngine,
        restore_engine: RestoreEngine,
        health_engine: HealthEngine,
        event_engine: EventEngine,
        audit_engine: AuditEngine,
        history_repository: OperationHistoryRepository,
    ) -> None:
        self._lifecycle_manager = lifecycle_manager
        self._validation_engine = validation_engine
        self._deployment_engine = deployment_engine
        self._backup_engine = backup_engine
        self._restore_engine = restore_engine
        self._health_engine = health_engine
        self._event_engine = event_engine
        self._audit_engine = audit_engine
        self._history_repository = history_repository

        # Active operations lock per project
        self._active_operations: dict[str, str] = {}
        self._lock = Lock()
        
        self._logger = StructuredLogger(component="operations_coordinator")
        self._retry_manager = RetryManager()
        self._recovery_manager = OperationRecoveryManager()
        self._event_reliability = EventReliabilityManager(DeadLetterQueue())

    def execute_operation(
        self,
        project_id: str,
        operation_type: OperationType,
        requested_by: str = "system",
        correlation_id: str | None = None,
        **kwargs,
    ) -> OperationResult:
        
        trace = get_current_trace()
        if trace:
            correlation_id = correlation_id or trace.correlation_id
        else:
            correlation_id = correlation_id or f"corr_{os.urandom(8).hex()}"
            
        operation_id = f"op_{os.urandom(8).hex()}"
        
        self._logger.info(
            "operation_request",
            f"Received request for {operation_type.value} on {project_id}",
            operation_id=operation_id,
            correlation_id=correlation_id,
            project_id=project_id,
        )

        try:
            self._acquire_lock(project_id, operation_id)
        except OperationConflictError as e:
            self._emit_event(
                event_type=f"{operation_type.value}_rejected",
                priority=EventPriority.NORMAL,
                correlation_id=correlation_id,
                payload={"project_id": project_id, "reason": "conflict"},
            )
            return OperationResult(
                operation_id=operation_id,
                status=OperationStatus.FAILED,
                completed_steps=(),
                failures=(str(e),),
            )

        try:
            plan = self._create_plan(operation_id, project_id, operation_type, correlation_id)
            
            self._emit_event(
                event_type=f"{operation_type.value}_started",
                priority=EventPriority.NORMAL,
                correlation_id=correlation_id,
                payload={"project_id": project_id, "operation_id": operation_id},
            )

            # Delegate to correct engine
            failures = []
            completed_steps = []
            
            with default_registry.measure_duration(f"operation_{operation_type.value}_duration"):
                def _do_operation():
                    nonlocal completed_steps, failures
                    completed_steps.clear()
                    failures.clear()
                    
                    if operation_type == OperationType.DEPLOY:
                        configuration = kwargs.get("configuration", {})
                        res = self._deployment_engine.deploy(
                            project_id=project_id, 
                            requested_by=requested_by,
                            configuration=configuration
                        )
                        completed_steps.append("deploy")
                        if not res.success: failures.append(res.message)
                    elif operation_type == OperationType.BACKUP:
                        res = self._backup_engine.backup(project_id=project_id, requested_by=requested_by)
                        completed_steps.append("backup")
                        if not res.success: failures.append(res.message)
                    elif operation_type == OperationType.RESTORE:
                        backup_id = kwargs.get("backup_id", "")
                        res = self._restore_engine.restore(project_id=project_id, backup_id=backup_id, requested_by=requested_by)
                        completed_steps.append("restore")
                        if not res.success: failures.append(res.message)
                    elif operation_type == OperationType.STOP:
                        self._lifecycle_manager.stop(project_id)
                        completed_steps.append("stop")
                    elif operation_type == OperationType.RESTART:
                        self._lifecycle_manager.stop(project_id)
                        completed_steps.append("stop")
                        self._lifecycle_manager.start(project_id)
                        completed_steps.append("start")
                    elif operation_type == OperationType.ARCHIVE:
                        self._lifecycle_manager.archive(project_id)
                        completed_steps.append("archive")
                    else:
                        failures.append(f"Unknown operation {operation_type}")
                        
                    if failures:
                        raise Exception(" | ".join(failures))

                try:
                    self._retry_manager.execute_with_retry(_do_operation)
                except RetryExhaustedError:
                    pass
                except NonRetryableError:
                    pass
                except Exception as e:
                    failures.append(str(e))
                    self._logger.error(
                        "operation_engine_error",
                        str(e),
                        operation_id=operation_id,
                        correlation_id=correlation_id,
                        project_id=project_id,
                    )

            status = OperationStatus.FAILED if failures else OperationStatus.COMPLETED
            
            if status == OperationStatus.FAILED:
                self._recovery_manager.capture_failure(
                    operation_id=operation_id,
                    project_id=project_id,
                    operation_type=operation_type.value,
                    error_message=str(failures),
                    context_payload={"correlation_id": correlation_id},
                )
                
                default_registry.increment_counter("operation_failure_count")
                if operation_type == OperationType.DEPLOY:
                    default_registry.increment_counter("deployment_failures")
                self._logger.warn(
                    "operation_failed",
                    f"Operation failed with {len(failures)} failures",
                    operation_id=operation_id,
                    correlation_id=correlation_id,
                    project_id=project_id,
                )
            else:
                default_registry.increment_counter("operation_success_count")
                if operation_type == OperationType.BACKUP:
                    # simplistic tracking for backup success rate calculation
                    default_registry.increment_counter("backup_success_count")
                self._logger.info(
                    "operation_completed",
                    "Operation completed successfully",
                    operation_id=operation_id,
                    correlation_id=correlation_id,
                    project_id=project_id,
                )
            
            self._audit_engine.record_event(
                category=AuditCategory.LIFECYCLE,
                event_type=f"operation_{operation_type.value}",
                severity=AuditSeverity.WARNING if failures else AuditSeverity.INFO,
                source_component="operations_coordinator",
                outcome_status=AuditStatus.FAILURE if failures else AuditStatus.SUCCESS,
                summary=f"Operation {operation_type.value} on {project_id}",
                target_identity=project_id,
                correlation_id=correlation_id,
                actor_context={"user": requested_by},
            )

            self._emit_event(
                event_type=f"{operation_type.value}_{status.value}",
                priority=EventPriority.HIGH if failures else EventPriority.NORMAL,
                correlation_id=correlation_id,
                payload={"project_id": project_id, "operation_id": operation_id, "failures": failures},
            )

            result = OperationResult(
                operation_id=operation_id,
                status=status,
                completed_steps=tuple(completed_steps),
                failures=tuple(failures),
            )
            
            self._history_repository.save_result(result, project_id)
            
            return result

        finally:
            self._release_lock(project_id, operation_id)

    def _create_plan(
        self, operation_id: str, project_id: str, operation_type: OperationType, correlation_id: str
    ) -> OperationPlan:
        return OperationPlan(
            operation_id=operation_id,
            project_id=project_id,
            operation_type=operation_type,
            requested_at=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            execution_steps=("validate", "execute", "verify"),
        )

    def _acquire_lock(self, project_id: str, operation_id: str) -> None:
        with self._lock:
            if project_id in self._active_operations:
                raise OperationConflictError(f"Project {project_id} already has an active operation.")
            self._active_operations[project_id] = operation_id

    def _release_lock(self, project_id: str, operation_id: str) -> None:
        with self._lock:
            if self._active_operations.get(project_id) == operation_id:
                del self._active_operations[project_id]

    def _emit_event(
        self, event_type: str, priority: EventPriority, correlation_id: str, payload: dict
    ) -> None:
        try:
            res = self._event_engine.publish(
                event_type=event_type,
                category=EventCategory.LIFECYCLE,
                priority=priority,
                payload=payload,
                correlation_id=correlation_id,
                source_component="operations_coordinator",
            )
            if not res.success:
                self._event_reliability.handle_delivery_failure(event_type, payload, Exception(res.message))
        except Exception as e:
            self._event_reliability.handle_delivery_failure(event_type, payload, e)
