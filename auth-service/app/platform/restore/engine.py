from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from app.platform.lifecycle import LifecycleManager
from app.platform.lifecycle.enums import LifecycleOperation, LifecycleState
from app.platform.restore.enums import (
    RestoreMode,
    RestoreStage,
    RestoreStatus,
    RestoreType,
)
from app.platform.restore.exceptions import (
    RestoreCompatibilityError,
    RestoreException,
    RestoreManifestError,
    RestorePlanError,
    RestoreRequestError,
    RestoreVerificationError,
)
from app.platform.restore.models import RestorePlan, RestoreResult
from app.platform.validation.engine import ValidationEngine
from app.platform.validation.enums import ValidationStatus
from app.project_registry import ProjectRegistryEntry
from app.project_registry_manager import ProjectRegistryManager


class RestoreEngine:
    """Deterministic, read-only restore coordinator."""

    def __init__(
        self,
        registry: ProjectRegistryManager,
        lifecycle_manager: LifecycleManager,
        validation_engine: ValidationEngine,
    ) -> None:
        self._registry = registry
        self._lifecycle_manager = lifecycle_manager
        self._validation_engine = validation_engine

    def create_plan(
        self,
        project_id: str,
        backup_id: str,
        restore_type: RestoreType = RestoreType.FULL,
        restore_mode: RestoreMode = RestoreMode.IN_PLACE,
        requested_by: str | None = None,
        timeout_seconds: int = 300,
    ) -> RestorePlan:
        self._validate_request(project_id, backup_id, restore_type, restore_mode, timeout_seconds)
        return RestorePlan(
            project_id=project_id,
            backup_id=backup_id,
            restore_type=restore_type,
            restore_mode=restore_mode,
            requested_by=requested_by,
            status=RestoreStatus.PLANNED,
            ordered_stages=self._default_stages(),
            dependencies=("registry", "lifecycle", "validation", "backup"),
            timeout_seconds=timeout_seconds,
            created_at=datetime.now(timezone.utc),
        )

    def restore(
        self,
        project_id: str,
        backup_id: str,
        restore_type: RestoreType = RestoreType.FULL,
        restore_mode: RestoreMode = RestoreMode.IN_PLACE,
        requested_by: str | None = None,
        timeout_seconds: int = 300,
    ) -> RestoreResult:
        started_at = datetime.now(timezone.utc)
        executed_stages: list[RestoreStage] = []
        plan: RestorePlan | None = None

        try:
            self._validate_request(project_id, backup_id, restore_type, restore_mode, timeout_seconds)
            executed_stages.append(RestoreStage.REQUEST_VALIDATION)
            
            # Validation via ValidationEngine
            validation_result = self._validation_engine.validate(project_id, LifecycleOperation.RESTORE)
            if validation_result.status is ValidationStatus.INVALID:
                raise RestoreRequestError(f"Validation failed for project {project_id}.")

            # Manifest Verification (Simulated)
            if not self._verify_manifest(backup_id):
                raise RestoreManifestError(f"Manifest verification failed for backup {backup_id}.")
            executed_stages.append(RestoreStage.MANIFEST_VERIFICATION)

            # Compatibility Check
            if not self._check_compatibility(project_id, backup_id):
                raise RestoreCompatibilityError("Backup is not compatible with current project state.")
            executed_stages.append(RestoreStage.COMPATIBILITY_CHECK)

            plan = self.create_plan(
                project_id=project_id,
                backup_id=backup_id,
                restore_type=restore_type,
                restore_mode=restore_mode,
                requested_by=requested_by,
                timeout_seconds=timeout_seconds,
            )
            executed_stages.append(RestoreStage.PLAN_CREATION)

            # Execution Orchestration
            self._execute_orchestration(plan)
            executed_stages.append(RestoreStage.EXECUTION_ORCHESTRATION)

            # Verification
            if not self._verify_restore(plan):
                raise RestoreVerificationError("Restore verification failed.")
            executed_stages.append(RestoreStage.RESTORE_VERIFICATION)

            executed_stages.append(RestoreStage.FINALIZATION)
            completed_at = datetime.now(timezone.utc)
            return self._finalize_result(
                plan=replace(plan, status=RestoreStatus.COMPLETED),
                executed_stages=tuple(executed_stages),
                started_at=started_at,
                completed_at=completed_at,
            )
        except RestoreException as error:
            if plan is None:
                # If plan creation failed, create a dummy one for the result
                plan = RestorePlan(
                    project_id=project_id,
                    backup_id=backup_id,
                    restore_type=restore_type,
                    restore_mode=restore_mode,
                    requested_by=requested_by,
                    status=RestoreStatus.FAILED,
                    ordered_stages=self._default_stages(),
                    dependencies=(),
                    timeout_seconds=timeout_seconds,
                    created_at=datetime.now(timezone.utc),
                )
            return RestoreResult(
                project_id=plan.project_id,
                backup_id=plan.backup_id,
                restore_type=plan.restore_type,
                restore_mode=plan.restore_mode,
                status=RestoreStatus.FAILED,
                plan=replace(plan, status=RestoreStatus.FAILED),
                executed_stages=tuple(executed_stages),
                verification_passed=False,
                success=False,
                message=str(error),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                failure_reason=str(error),
            )

    def _finalize_result(
        self,
        *,
        plan: RestorePlan,
        executed_stages: tuple[RestoreStage, ...],
        started_at: datetime,
        completed_at: datetime,
    ) -> RestoreResult:
        return RestoreResult(
            project_id=plan.project_id,
            backup_id=plan.backup_id,
            restore_type=plan.restore_type,
            restore_mode=plan.restore_mode,
            status=plan.status,
            plan=plan,
            executed_stages=executed_stages,
            verification_passed=True,
            success=True,
            message="Restore completed successfully.",
            started_at=started_at,
            completed_at=completed_at,
        )

    def _validate_request(
        self,
        project_id: str,
        backup_id: str,
        restore_type: RestoreType,
        restore_mode: RestoreMode,
        timeout_seconds: int,
    ) -> None:
        if not project_id.strip():
            raise RestoreRequestError("Project ID is required.")

        if not backup_id.strip():
            raise RestoreRequestError("Backup ID is required.")

        if timeout_seconds <= 0:
            raise RestoreRequestError("Timeout must be positive.")

        if restore_type not in tuple(RestoreType):
            raise RestoreRequestError(f"Unsupported restore type: {restore_type!r}")

        if restore_mode not in tuple(RestoreMode):
            raise RestoreRequestError(f"Unsupported restore mode: {restore_mode!r}")

        project = self._registry.get_by_project_id(project_id)
        if project is None and restore_mode is RestoreMode.IN_PLACE:
            raise RestoreRequestError(f"Unknown project for in-place restore: {project_id}")

        current_state = self._resolve_state(project_id)
        if current_state is LifecycleState.ARCHIVED and restore_mode is RestoreMode.IN_PLACE:
            raise RestoreRequestError(f"Archived projects cannot be restored in-place: {project_id}")

    def _verify_manifest(self, backup_id: str) -> bool:
        # Simulated verification
        return backup_id.startswith("bkp_")

    def _check_compatibility(self, project_id: str, backup_id: str) -> bool:
        # Simulated compatibility check
        return True

    def _execute_orchestration(self, plan: RestorePlan) -> None:
        # Simulated orchestration
        pass

    def _verify_restore(self, plan: RestorePlan) -> bool:
        # Simulated verification
        return True

    def _resolve_state(self, project_id: str) -> LifecycleState | None:
        state_map = getattr(self._lifecycle_manager, "_states", None)
        if isinstance(state_map, dict):
            return state_map.get(project_id)

        get_state = getattr(self._lifecycle_manager, "get_state", None)
        if callable(get_state):
            return get_state(project_id)

        return None

    @staticmethod
    def _default_stages() -> tuple[RestoreStage, ...]:
        return (
            RestoreStage.REQUEST_VALIDATION,
            RestoreStage.MANIFEST_VERIFICATION,
            RestoreStage.COMPATIBILITY_CHECK,
            RestoreStage.PLAN_CREATION,
            RestoreStage.EXECUTION_ORCHESTRATION,
            RestoreStage.RESTORE_VERIFICATION,
            RestoreStage.FINALIZATION,
        )
