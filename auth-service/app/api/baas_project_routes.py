from app.api.rate_limiter import rate_limit_ip, rate_limit_api_key
from fastapi import APIRouter, Depends, status
from app.api.baas_models import BaaSProjectCreateRequest, BaaSProjectResponse
from app.api.models import (
    DeployRequest, BackupRequest, RestoreRequest, OperationResponse,
    HealthResponse, ValidateResponse, StopRequest, RestartRequest, LogsResponse,
    ProjectStatusResponse, OperationHistoryResponse, ProjectMetricsResponse,
)
from app.api.dependencies import get_current_user, get_baas_project_service, require_viewer, require_developer, require_admin, require_owner
from app.api.baas_service import BaaSProjectServiceLayer
from app.identity.models import DeveloperUser

router = APIRouter(prefix="/projects", tags=["BaaS Projects"])

@router.post("/", response_model=BaaSProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    req: BaaSProjectCreateRequest,
    user: DeveloperUser = Depends(get_current_user),
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.create_project(user.user_id, req)

@router.get("/", response_model=list[BaaSProjectResponse])
def list_projects(
    user: DeveloperUser = Depends(get_current_user),
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.list_projects(user.user_id)

@router.get("/{project_id}", response_model=BaaSProjectResponse)
def get_project(
    project_id: str,
    user: DeveloperUser = Depends(get_current_user),
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    # require_viewer ensures the user has at least read access
    role: str = Depends(require_viewer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.get_project(project_id)

@router.post("/{project_id}/deploy", response_model=OperationResponse)
def deploy_project(
    project_id: str,
    req: DeployRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_developer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.deploy_project(project_id, req)

@router.post("/{project_id}/backup", response_model=OperationResponse)
def backup_project(
    project_id: str,
    req: BackupRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.backup_project(project_id, req)

@router.post("/{project_id}/restore", response_model=OperationResponse)
def restore_project(
    project_id: str,
    req: RestoreRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.restore_project(project_id, req)

@router.post("/{project_id}/validate", response_model=ValidateResponse)
def validate_project(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_developer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.validate_project(project_id)

@router.get("/{project_id}/health", response_model=HealthResponse)
def get_health(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_viewer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.get_health(project_id)

@router.post("/{project_id}/stop", response_model=OperationResponse)
def stop_project(
    project_id: str,
    req: StopRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_developer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.stop_project(project_id, req)

@router.post("/{project_id}/restart", response_model=OperationResponse)
def restart_project(
    project_id: str,
    req: RestartRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_developer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.restart_project(project_id, req)

@router.get("/{project_id}/logs", response_model=LogsResponse)
def get_project_logs(
    project_id: str,
    limit: int = 100,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_viewer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.get_project_logs(project_id, limit)

from app.api.baas_models import ProjectMemberResponse, AddMemberRequest, UpdateMemberRoleRequest, ApiKeyCreateRequest, ApiKeyResponse, ApiKeyListResponse
from app.api.dependencies import verify_project_api_key
from app.api.rate_limiter import rate_limit_ip, rate_limit_api_key

from app.api.baas_models import TableCreateRequest, TableResponse, RowCreateResponse, RowResponse
from typing import Dict, Any

# ================== DATA PLANE (API KEY) ==================

@router.post("/{project_id}/data/{table_name}", response_model=RowCreateResponse, status_code=status.HTTP_201_CREATED)
def insert_row(
    project_id: str,
    table_name: str,
    data: Dict[str, Any],
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    verified_project_id: str = Depends(verify_project_api_key),
    _rate_limit: None = Depends(rate_limit_api_key),
):
    row_id = service.insert_row(verified_project_id, table_name, data)
    return {"id": row_id}

@router.get("/{project_id}/data/{table_name}", response_model=list[RowResponse])
def list_rows(
    project_id: str,
    table_name: str,
    limit: int = 100,
    offset: int = 0,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    verified_project_id: str = Depends(verify_project_api_key),
    _rate_limit: None = Depends(rate_limit_api_key),
):
    rows = service.list_rows(verified_project_id, table_name, limit, offset)
    return [{"data": r} for r in rows]

@router.get("/{project_id}/data/{table_name}/{row_id}", response_model=RowResponse)
def get_row(
    project_id: str,
    table_name: str,
    row_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    verified_project_id: str = Depends(verify_project_api_key),
    _rate_limit: None = Depends(rate_limit_api_key),
):
    row = service.get_row(verified_project_id, table_name, row_id)
    return {"data": row}

@router.put("/{project_id}/data/{table_name}/{row_id}")
def update_row(
    project_id: str,
    table_name: str,
    row_id: str,
    data: Dict[str, Any],
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    verified_project_id: str = Depends(verify_project_api_key),
    _rate_limit: None = Depends(rate_limit_api_key),
):
    service.update_row(verified_project_id, table_name, row_id, data)
    return {"status": "success"}

@router.delete("/{project_id}/data/{table_name}/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_row(
    project_id: str,
    table_name: str,
    row_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    verified_project_id: str = Depends(verify_project_api_key),
    _rate_limit: None = Depends(rate_limit_api_key),
):
    service.delete_row(verified_project_id, table_name, row_id)


@router.post("/{project_id}/keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    project_id: str,
    req: ApiKeyCreateRequest,
    user: DeveloperUser = Depends(get_current_user),
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.create_api_key(project_id, req.name, user.user_id)

@router.get("/{project_id}/keys", response_model=list[ApiKeyListResponse])
def list_api_keys(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.list_api_keys(project_id)

@router.delete("/{project_id}/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    project_id: str,
    key_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    service.revoke_api_key(project_id, key_id)

@router.post("/{project_id}/keys/{key_id}/rotate", response_model=ApiKeyResponse)
def rotate_api_key(
    project_id: str,
    key_id: str,
    user: DeveloperUser = Depends(get_current_user),
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.rotate_api_key(project_id, key_id, user.user_id)

@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
def list_members(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_viewer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.list_members(project_id)

@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: str,
    req: AddMemberRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.add_member(project_id, req.email, req.role.value, role)

@router.put("/{project_id}/members/{target_user_id}", response_model=ProjectMemberResponse)
def update_member_role(
    project_id: str,
    target_user_id: str,
    req: UpdateMemberRoleRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.update_member_role(project_id, target_user_id, req.role.value, role)

@router.delete("/{project_id}/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: str,
    target_user_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    service.remove_member(project_id, target_user_id, role)

# ================== CONTROL PLANE (TABLE SCHEMA) ==================

@router.post("/{project_id}/tables", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
def create_table(
    project_id: str,
    req: TableCreateRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    service.create_table(project_id, req.name, req.columns)
    return {"name": req.name}

@router.get("/{project_id}/tables", response_model=list[TableResponse])
def list_tables(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_viewer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    tables = service.list_tables(project_id)
    return [{"name": t} for t in tables]

@router.get("/{project_id}/tables/{table_name}")
def get_table_schema(
    project_id: str,
    table_name: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_viewer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    return service.get_table_schema(project_id, table_name)

@router.delete("/{project_id}/tables/{table_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table(
    project_id: str,
    table_name: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
    _rate_limit: None = Depends(rate_limit_ip),
):
    service.delete_table(project_id, table_name)


# ─── Phase 14.4 Monitoring endpoints ──────────────────────────────────────────

@router.get("/{project_id}/status", response_model=ProjectStatusResponse)
def get_project_status(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_viewer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    """Return the current lifecycle and deployment status for the project.
    Deployment handle tracking is in-process only; status is marked simulated."""
    return service.get_project_status(project_id)


@router.get("/{project_id}/history", response_model=OperationHistoryResponse)
def get_project_history(
    project_id: str,
    limit: int = 100,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_viewer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    """Return paginated operation history for the project (newest first, max 500)."""
    return service.get_project_history(project_id, limit=limit)


@router.get("/{project_id}/metrics", response_model=ProjectMetricsResponse)
def get_project_metrics(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_developer),
    _rate_limit: None = Depends(rate_limit_ip),
):
    """Return process-global operation counters since last restart.
    Requires Developer role; Viewers are rejected."""
    return service.get_project_metrics(project_id)
