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
    pass


class BackupRequest(BaseOperationRequest):
    backup_type: str = "full"


class RestoreRequest(BaseOperationRequest):
    backup_id: str


class OperationResponse(BaseModel):
    operation_id: str
    status: str
    completed_steps: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    project_id: str
    state: str
    status: str
    success: bool
    message: str
