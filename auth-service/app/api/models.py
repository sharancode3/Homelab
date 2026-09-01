from typing import Any
from pydantic import BaseModel, Field


class ProjectRegisterRequest(BaseModel):
    project_id: str
    project_name: str
    project_slug: str
    project_type: str = "backend"
    project_version: str = "1.0.0"


class ProjectRegisterResponse(BaseModel):
    project_id: str
    status: str
    message: str


class ValidateResponse(BaseModel):
    project_id: str
    is_valid: bool
    issues: list[str] = Field(default_factory=list)


class BaseOperationRequest(BaseModel):
    requested_by: str = "system"
    correlation_id: str | None = None


class DeployRequest(BaseOperationRequest):
    configuration: dict[str, Any] = Field(default_factory=dict)


class BackupRequest(BaseOperationRequest):
    backup_type: str = "full"


class RestoreRequest(BaseOperationRequest):
    backup_id: str


class OperationResponse(BaseModel):
    operation_id: str
    status: str
    completed_steps: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    project_id: str
    state: str
    status: str
    success: bool
    message: str


class StopRequest(BaseOperationRequest):
    pass


class RestartRequest(BaseOperationRequest):
    pass


class LogEventResponse(BaseModel):
    audit_id: str
    timestamp: str
    event_type: str
    severity: str
    message: str


class LogsResponse(BaseModel):
    project_id: str
    logs: list[LogEventResponse] = Field(default_factory=list)


# ─── Phase 14.4 Monitoring Models ────────────────────────────────────────────

class ProjectStatusResponse(BaseModel):
    project_id: str
    lifecycle_state: str          # e.g. "deployed", "stopped", "registered"
    deployment_status: str        # e.g. "completed", "unknown"
    simulated: bool = True        # True until real Docker runtime exists
    message: str


class OperationHistoryEntry(BaseModel):
    operation_id: str
    status: str
    completed_steps: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)


class OperationHistoryResponse(BaseModel):
    project_id: str
    total_returned: int
    history: list[OperationHistoryEntry] = Field(default_factory=list)


class ProjectMetricsResponse(BaseModel):
    project_id: str
    since_restart: bool = True    # Always True: counters are in-memory only
    operation_success_count: int = 0
    operation_failure_count: int = 0
    deployment_failures: int = 0
    backup_success_count: int = 0
    avg_operation_duration_ms: float = 0.0


class PlatformMetricsResponse(BaseModel):
    cpu_percent: float
    memory_total_mb: float
    memory_available_mb: float
    memory_used_percent: float
    disk_total_mb: float
    disk_used_mb: float
    disk_used_percent: float
    since_restart_counters: dict[str, int] = Field(default_factory=dict)
    since_restart_avg_durations_ms: dict[str, float] = Field(default_factory=dict)
    collected_at: str
