from dataclasses import dataclass
from datetime import datetime

from app.platform.deployment.enums import DeploymentStage, DeploymentStatus


@dataclass(frozen=True, slots=True)
class DeploymentPlan:
    project_id: str
    project_slug: str
    project_name: str
    requested_by: str | None
    status: DeploymentStatus
    ordered_stages: tuple[DeploymentStage, ...]
    dependencies: tuple[str, ...]
    timeout_seconds: int
    retry_count: int
    verification_required: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DeploymentResult:
    project_id: str
    project_slug: str
    project_name: str
    status: DeploymentStatus
    plan: DeploymentPlan
    executed_stages: tuple[DeploymentStage, ...]
    verification_passed: bool
    success: bool
    message: str
    started_at: datetime
    completed_at: datetime
    failure_reason: str | None = None
