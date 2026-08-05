from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.platform.operations.enums import OperationStatus, OperationType


@dataclass(frozen=True, slots=True)
class OperationPlan:
    operation_id: str
    project_id: str
    operation_type: OperationType
    requested_at: datetime
    correlation_id: str
    execution_steps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OperationResult:
    operation_id: str
    status: OperationStatus
    completed_steps: tuple[str, ...]
    failures: tuple[str, ...]
    compensation_result: dict[str, Any] = field(default_factory=dict)
