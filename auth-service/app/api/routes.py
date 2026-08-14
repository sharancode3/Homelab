from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies import verify_internal_token
from app.api.baas_project_routes import router as baas_project_router
from app.api.baas_auth_routes import router as baas_auth_router

from app.api.models import (
    BackupRequest,
    DeployRequest,
    HealthResponse,
    OperationResponse,
    ProjectRegisterRequest,
    ProjectRegisterResponse,
    RestoreRequest,
    ValidateResponse,
)
from app.api.service import APIServiceLayer

# We will inject the service layer via FastAPI dependencies in real usage,
# but for now, we leave a placeholder for `get_service` dependency.
# In `main.py` or tests, this dependency will be overridden.

def get_api_service() -> APIServiceLayer:
    raise NotImplementedError("Dependency should be overridden in app startup.")

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(verify_internal_token)])

@router.post("/register", response_model=ProjectRegisterResponse)
def register_project(
    req: ProjectRegisterRequest, service: APIServiceLayer = Depends(get_api_service)
) -> ProjectRegisterResponse:
    try:
        return service.register_project(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/validate", response_model=ValidateResponse)
def validate_project(
    project_id: str, service: APIServiceLayer = Depends(get_api_service)
) -> ValidateResponse:
    try:
        return service.validate_project(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/deploy", response_model=OperationResponse)
def deploy_project(
    project_id: str, req: DeployRequest, service: APIServiceLayer = Depends(get_api_service)
) -> OperationResponse:
    try:
        return service.deploy_project(project_id, req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/backup", response_model=OperationResponse)
def backup_project(
    project_id: str, req: BackupRequest, service: APIServiceLayer = Depends(get_api_service)
) -> OperationResponse:
    try:
        return service.backup_project(project_id, req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/restore", response_model=OperationResponse)
def restore_project(
    project_id: str, req: RestoreRequest, service: APIServiceLayer = Depends(get_api_service)
) -> OperationResponse:
    try:
        return service.restore_project(project_id, req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/health", response_model=HealthResponse)
def get_health(
    project_id: str, service: APIServiceLayer = Depends(get_api_service)
) -> HealthResponse:
    try:
        return service.get_health(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
