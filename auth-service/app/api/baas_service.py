import secrets
import random
from fastapi import HTTPException
from app.api.baas_models import BaaSProjectCreateRequest, BaaSProjectResponse
from app.api.models import ProjectRegisterRequest, DeployRequest, BackupRequest, RestoreRequest, OperationResponse, HealthResponse, ValidateResponse
from app.api.service import APIServiceLayer
from app.storage.interfaces import ProjectAuthorizationRepository
from app.project_registry_manager import ProjectRegistryManager

class BaaSProjectServiceLayer:
    def __init__(
        self,
        internal_service: APIServiceLayer,
        authz_repo: ProjectAuthorizationRepository,
        registry: ProjectRegistryManager,
    ) -> None:
        self._internal = internal_service
        self._authz = authz_repo
        self._registry = registry

    def create_project(self, user_id: str, req: BaaSProjectCreateRequest) -> BaaSProjectResponse:
        # Generate project ID securely with digits to match pattern '^proj_\d{4,}$'
        random_digits = "".join(random.choices("0123456789", k=8))
        project_id = f"proj_{random_digits}"
        
        internal_req = ProjectRegisterRequest(
            project_id=project_id,
            project_name=req.project_name,
            project_slug=req.project_slug,
            project_type=req.project_type,
            project_version=req.project_version,
        )
        
        # 1. Register with infrastructure
        self._internal.register_project(internal_req)
        
        # 2. Assign ownership
        self._authz.add_member(project_id, user_id, "owner")
        
        entry = self._registry.get_by_project_id(project_id)
        if not entry:
            raise HTTPException(status_code=500, detail="Project creation failed internally")
            
        return BaaSProjectResponse(
            project_id=project_id,
            project_name=entry.project_name,
            project_slug=entry.project_slug,
            project_type=entry.project_type.value,
            status=entry.status.value,
            project_version=entry.project_version,
        )
        
    def list_projects(self, user_id: str) -> list[BaaSProjectResponse]:
        project_ids = self._authz.get_projects_for_user(user_id)
        responses = []
        for pid in project_ids:
            entry = self._registry.get_by_project_id(pid)
            if entry:
                responses.append(
                    BaaSProjectResponse(
                        project_id=entry.project_id,
                        project_name=entry.project_name,
                        project_slug=entry.project_slug,
                        project_type=entry.project_type.value,
                        status=entry.status.value,
                        project_version=entry.project_version,
                    )
                )
        return responses

    def get_project(self, project_id: str) -> BaaSProjectResponse:
        entry = self._registry.get_by_project_id(project_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Project not found")
            
        return BaaSProjectResponse(
            project_id=entry.project_id,
            project_name=entry.project_name,
            project_slug=entry.project_slug,
            project_type=entry.project_type.value,
            status=entry.status.value,
            project_version=entry.project_version,
        )

    def deploy_project(self, project_id: str, req: DeployRequest) -> OperationResponse:
        return self._internal.deploy_project(project_id, req)

    def backup_project(self, project_id: str, req: BackupRequest) -> OperationResponse:
        return self._internal.backup_project(project_id, req)

    def restore_project(self, project_id: str, req: RestoreRequest) -> OperationResponse:
        return self._internal.restore_project(project_id, req)

    def validate_project(self, project_id: str) -> ValidateResponse:
        return self._internal.validate_project(project_id)

    def get_health(self, project_id: str) -> HealthResponse:
        return self._internal.get_health(project_id)
