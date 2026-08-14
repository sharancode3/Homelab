from fastapi import APIRouter, Depends, status
from app.api.baas_models import BaaSProjectCreateRequest, BaaSProjectResponse
from app.api.models import DeployRequest, BackupRequest, RestoreRequest, OperationResponse, HealthResponse, ValidateResponse
from app.api.dependencies import get_current_user, get_baas_project_service, require_viewer, require_developer, require_admin, require_owner
from app.api.baas_service import BaaSProjectServiceLayer
from app.identity.models import DeveloperUser

router = APIRouter(prefix="/projects", tags=["BaaS Projects"])

@router.post("/", response_model=BaaSProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    req: BaaSProjectCreateRequest,
    user: DeveloperUser = Depends(get_current_user),
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
):
    return service.create_project(user.user_id, req)

@router.get("/", response_model=list[BaaSProjectResponse])
def list_projects(
    user: DeveloperUser = Depends(get_current_user),
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
):
    return service.list_projects(user.user_id)

@router.get("/{project_id}", response_model=BaaSProjectResponse)
def get_project(
    project_id: str,
    user: DeveloperUser = Depends(get_current_user),
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    # require_viewer ensures the user has at least read access
    role: str = Depends(require_viewer),
):
    return service.get_project(project_id)

@router.post("/{project_id}/deploy", response_model=OperationResponse)
def deploy_project(
    project_id: str,
    req: DeployRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_developer),
):
    return service.deploy_project(project_id, req)

@router.post("/{project_id}/backup", response_model=OperationResponse)
def backup_project(
    project_id: str,
    req: BackupRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
):
    return service.backup_project(project_id, req)

@router.post("/{project_id}/restore", response_model=OperationResponse)
def restore_project(
    project_id: str,
    req: RestoreRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
):
    return service.restore_project(project_id, req)

@router.post("/{project_id}/validate", response_model=ValidateResponse)
def validate_project(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_developer),
):
    return service.validate_project(project_id)

@router.get("/{project_id}/health", response_model=HealthResponse)
def get_health(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_viewer),
):
    return service.get_health(project_id)

from app.api.baas_models import ProjectMemberResponse, AddMemberRequest, UpdateMemberRoleRequest, ApiKeyCreateRequest, ApiKeyResponse, ApiKeyListResponse
from app.api.dependencies import verify_project_api_key

@router.get("/{project_id}/data/test", response_model=dict)
def data_plane_test(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    verified_project_id: str = Depends(verify_project_api_key),
):
    return {"status": "success", "project_id": verified_project_id, "message": "Data plane accessed via API key"}

@router.post("/{project_id}/keys", response_model=ApiKeyResponse)
def create_api_key(
    project_id: str,
    req: ApiKeyCreateRequest,
    user: DeveloperUser = Depends(get_current_user),
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
):
    return service.create_api_key(project_id, req.name, user.user_id)

@router.get("/{project_id}/keys", response_model=list[ApiKeyListResponse])
def list_api_keys(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
):
    return service.list_api_keys(project_id)

@router.delete("/{project_id}/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    project_id: str,
    key_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
):
    service.revoke_api_key(project_id, key_id)

@router.post("/{project_id}/keys/{key_id}/rotate", response_model=ApiKeyResponse)
def rotate_api_key(
    project_id: str,
    key_id: str,
    user: DeveloperUser = Depends(get_current_user),
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
):
    return service.rotate_api_key(project_id, key_id, user.user_id)

@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
def list_members(
    project_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_viewer),
):
    return service.list_members(project_id)

@router.post("/{project_id}/members", response_model=ProjectMemberResponse)
def add_member(
    project_id: str,
    req: AddMemberRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
):
    return service.add_member(project_id, req.email, req.role.value, role)

@router.put("/{project_id}/members/{target_user_id}", response_model=ProjectMemberResponse)
def update_member_role(
    project_id: str,
    target_user_id: str,
    req: UpdateMemberRoleRequest,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
):
    return service.update_member_role(project_id, target_user_id, req.role.value, role)

@router.delete("/{project_id}/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: str,
    target_user_id: str,
    service: BaaSProjectServiceLayer = Depends(get_baas_project_service),
    role: str = Depends(require_admin),
):
    service.remove_member(project_id, target_user_id, role)
