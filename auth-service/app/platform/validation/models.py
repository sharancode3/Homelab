from dataclasses import dataclass
from datetime import datetime

from app.platform.lifecycle.enums import LifecycleOperation, LifecycleState
from app.platform.validation.enums import ValidationCategory, ValidationStatus


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    validation_id: str
    category: ValidationCategory
    status: ValidationStatus
    message: str
    details: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    project_id: str
    project_slug: str | None
    project_name: str | None
    operation: LifecycleOperation | str
    current_state: LifecycleState | None
    status: ValidationStatus
    issues: tuple[ValidationIssue, ...]
    evaluated_at: datetime
    report_version: str = "1.0"

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue for issue in self.issues if issue.status is ValidationStatus.WARNING
        )

    @property
    def invalid_issues(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue for issue in self.issues if issue.status is ValidationStatus.INVALID
        )

    @property
    def is_valid(self) -> bool:
        return self.status is ValidationStatus.VALID


@dataclass(frozen=True, slots=True)
class ValidationContext:
    project_id: str
    requested_operation: LifecycleOperation | str
    operation: LifecycleOperation | None
    project: object | None
    current_state: LifecycleState | None
    project_slug: str | None
    project_name: str | None
