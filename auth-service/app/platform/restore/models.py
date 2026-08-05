from dataclasses import dataclass
from datetime import datetime

from app.platform.restore.enums import (
    RestoreMode,
    RestoreStage,
    RestoreStatus,
    RestoreType,
)


@dataclass(frozen=True, slots=True)
class RestorePlan:
    project_id: str
    backup_id: str
    restore_type: RestoreType
    restore_mode: RestoreMode
    requested_by: str | None
    status: RestoreStatus
    ordered_stages: tuple[RestoreStage, ...]
    dependencies: tuple[str, ...]
    timeout_seconds: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RestoreResult:
    project_id: str
    backup_id: str
    restore_type: RestoreType
    restore_mode: RestoreMode
    status: RestoreStatus
    plan: RestorePlan
    executed_stages: tuple[RestoreStage, ...]
    verification_passed: bool
    success: bool
    message: str
    started_at: datetime
    completed_at: datetime
    failure_reason: str | None = None
