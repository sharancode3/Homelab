from collections.abc import Sequence
from datetime import datetime, timezone

from app.platform.lifecycle import LifecycleManager
from app.platform.lifecycle.enums import LifecycleOperation, LifecycleState
from app.platform.validation.enums import ValidationStatus
from app.platform.validation.models import (
    ValidationContext,
    ValidationIssue,
    ValidationResult,
)
from app.platform.validation.validators import (
    ConfigurationValidator,
    LifecycleValidator,
    OperationValidator,
    ProjectValidator,
    RequestValidator,
    Validator,
)
from app.project_registry_manager import ProjectRegistryManager


class ValidationEngine:
    """Deterministic, read-only validation pipeline for lifecycle operations."""

    def __init__(
        self,
        registry: ProjectRegistryManager,
        lifecycle_manager: LifecycleManager,
        validators: Sequence[Validator] | None = None,
    ) -> None:
        self._registry = registry
        self._lifecycle_manager = lifecycle_manager
        self._validators: tuple[Validator, ...] = tuple(
            validators
            if validators is not None
            else (
                RequestValidator(),
                ProjectValidator(),
                LifecycleValidator(),
                ConfigurationValidator(),
                OperationValidator(),
            )
        )

    def validate(
        self,
        project_id: str,
        operation: LifecycleOperation | str,
    ) -> ValidationResult:
        normalized_operation = self._normalize_operation(operation)
        project = self._registry.get_by_project_id(project_id)
        current_state = self._resolve_current_state(project_id)
        context = ValidationContext(
            project_id=project_id,
            requested_operation=operation,
            operation=normalized_operation,
            project=project,
            current_state=current_state,
            project_slug=getattr(project, "project_slug", None),
            project_name=getattr(project, "project_name", None),
        )

        issues: list[ValidationIssue] = []
        for validator in self._validators:
            issues.extend(validator.validate(context))

        status = self._aggregate_status(issues)
        return ValidationResult(
            project_id=project_id,
            project_slug=context.project_slug,
            project_name=context.project_name,
            operation=operation,
            current_state=current_state,
            status=status,
            issues=tuple(issues),
            evaluated_at=datetime.now(timezone.utc),
        )

    def _resolve_current_state(self, project_id: str) -> LifecycleState | None:
        state_map = getattr(self._lifecycle_manager, "_states", None)
        if isinstance(state_map, dict):
            return state_map.get(project_id)

        get_state = getattr(self._lifecycle_manager, "get_state", None)
        if callable(get_state):
            return get_state(project_id)

        return None

    def _normalize_operation(
        self, operation: LifecycleOperation | str
    ) -> LifecycleOperation | None:
        if isinstance(operation, LifecycleOperation):
            return operation

        try:
            return LifecycleOperation(operation)
        except ValueError:
            return None

    def _aggregate_status(
        self, issues: Sequence[ValidationIssue]
    ) -> ValidationStatus:
        if any(issue.status is ValidationStatus.INVALID for issue in issues):
            return ValidationStatus.INVALID

        if any(issue.status is ValidationStatus.WARNING for issue in issues):
            return ValidationStatus.WARNING

        return ValidationStatus.VALID
