from dataclasses import dataclass
from typing import Protocol

from app.platform.lifecycle.enums import LifecycleOperation, LifecycleState
from app.platform.validation.enums import ValidationCategory, ValidationStatus
from app.platform.validation.models import ValidationContext, ValidationIssue


class Validator(Protocol):
    def validate(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        ...


@dataclass(frozen=True, slots=True)
class RequestValidator:
    def validate(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        if not context.project_id.strip():
            issues.append(
                ValidationIssue(
                    validation_id="REQ001",
                    category=ValidationCategory.OPERATION,
                    status=ValidationStatus.INVALID,
                    message="Project ID is required.",
                )
            )
        if context.operation is None:
            issues.append(
                ValidationIssue(
                    validation_id="REQ002",
                    category=ValidationCategory.OPERATION,
                    status=ValidationStatus.INVALID,
                    message=(
                        f"Unsupported lifecycle operation: {context.requested_operation!r}."
                    ),
                )
            )
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class ProjectValidator:
    def validate(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        if context.project is None:
            return (
                ValidationIssue(
                    validation_id="REG001",
                    category=ValidationCategory.REGISTRY,
                    status=ValidationStatus.INVALID,
                    message=f"Unknown project: {context.project_id}",
                ),
            )

        return ()


@dataclass(frozen=True, slots=True)
class LifecycleValidator:
    def validate(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        if context.project is None:
            return ()

        current_state = context.current_state
        if context.operation is LifecycleOperation.REGISTER:
            if current_state is None:
                return ()

            return (
                ValidationIssue(
                    validation_id="LIFE003",
                    category=ValidationCategory.LIFECYCLE,
                    status=ValidationStatus.INVALID,
                    message=(
                        f"Project is already registered with lifecycle state "
                        f"{current_state.value}."
                    ),
                ),
            )

        if current_state is None:
            return (
                ValidationIssue(
                    validation_id="LIFE001",
                    category=ValidationCategory.LIFECYCLE,
                    status=ValidationStatus.INVALID,
                    message=f"Project has no lifecycle state: {context.project_id}",
                ),
            )

        allowed_states: dict[LifecycleOperation, tuple[LifecycleState, ...]] = {
            LifecycleOperation.VALIDATE: (LifecycleState.REGISTERED,),
            LifecycleOperation.DEPLOY: (LifecycleState.VALIDATED,),
            LifecycleOperation.START: (LifecycleState.DEPLOYED, LifecycleState.STOPPED),
            LifecycleOperation.STOP: (LifecycleState.RUNNING, LifecycleState.DEPLOYED),
            LifecycleOperation.ARCHIVE: (
                LifecycleState.RUNNING,
                LifecycleState.STOPPED,
                LifecycleState.FAILED,
            ),
            LifecycleOperation.FAIL: (
                LifecycleState.REGISTERED,
                LifecycleState.VALIDATED,
                LifecycleState.DEPLOYED,
                LifecycleState.RUNNING,
                LifecycleState.STOPPED,
            ),
        }

        if current_state not in allowed_states[context.operation]:
            return (
                ValidationIssue(
                    validation_id="LIFE002",
                    category=ValidationCategory.LIFECYCLE,
                    status=ValidationStatus.INVALID,
                    message=(
                        f"Operation {context.operation.value} is not allowed from "
                        f"state {current_state.value}."
                    ),
                ),
            )

        return ()


@dataclass(frozen=True, slots=True)
class ConfigurationValidator:
    def validate(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        if context.project is None:
            return ()

        project_version = getattr(context.project, "project_version", None)
        if project_version is None:
            return (
                ValidationIssue(
                    validation_id="CFG001",
                    category=ValidationCategory.CONFIGURATION,
                    status=ValidationStatus.WARNING,
                    message="Project version is not set.",
                ),
            )

        return ()


@dataclass(frozen=True, slots=True)
class OperationValidator:
    def validate(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        if context.project is None or context.operation is None:
            return ()

        return ()
