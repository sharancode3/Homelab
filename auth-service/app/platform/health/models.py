from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.platform.health.enums import (
    HealthCategory,
    HealthSeverity,
    HealthState,
    HealthStatus,
)


@dataclass(frozen=True, slots=True)
class HealthIndicator:
    indicator_id: str
    name: str
    category: HealthCategory
    state: HealthState
    severity: HealthSeverity
    details: dict[str, Any]
    checked_at: datetime


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    project_id: str
    project_slug: str | None
    project_name: str | None
    state: HealthState
    status: HealthStatus
    indicators: tuple[HealthIndicator, ...]
    evaluated_at: datetime
    message: str
    success: bool
    failure_reason: str | None = None
