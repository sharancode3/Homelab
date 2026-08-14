import secrets
import random
import secrets
import hashlib
from fastapi import HTTPException
from app.api.baas_models import BaaSProjectCreateRequest, BaaSProjectResponse
from app.api.models import ProjectRegisterRequest, DeployRequest, BackupRequest, RestoreRequest, OperationResponse, HealthResponse, ValidateResponse
from app.api.service import APIServiceLayer
from app.storage.interfaces import ProjectAuthorizationRepository, UserRepository
from app.project_registry_manager import ProjectRegistryManager

class BaaSProjectServiceLayer:
    def __init__(
        self,
        internal_service: APIServiceLayer,
        authz_repo: ProjectAuthorizationRepository,
        registry: ProjectRegistryManager,
        user_repo: UserRepository,
        tenant_db: "TenantDatabaseManager" = None,
    ) -> None:
        self._internal = internal_service
        self._authz = authz_repo
        self._registry = registry
        self._user_repo = user_repo
        self._tenant_db = tenant_db

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

    # Membership Management
    def list_members(self, project_id: str) -> list[dict]:
        members = self._authz.get_project_members(project_id)
        result = []
        for m in members:
            u = self._user_repo.get_by_user_id(m["user_id"])
            if u:
                result.append({"user_id": u.user_id, "email": u.email, "role": m["role"]})
        return result

    def add_member(self, project_id: str, email: str, role: str, actor_role: str) -> dict:
        if role == "owner" and actor_role != "owner":
            raise HTTPException(status_code=403, detail="Only owners can add new owners")

        target_user = self._user_repo.get_by_email(email)
        if not target_user:
            raise HTTPException(status_code=404, detail="User with this email not found")

        existing_role = self._authz.get_role(project_id, target_user.user_id)
        if existing_role:
            raise HTTPException(status_code=400, detail="User is already a member of this project")

        self._authz.add_member(project_id, target_user.user_id, role)
        return {"user_id": target_user.user_id, "email": target_user.email, "role": role}

    def update_member_role(self, project_id: str, target_user_id: str, new_role: str, actor_role: str) -> dict:
        target_role = self._authz.get_role(project_id, target_user_id)
        if not target_role:
            raise HTTPException(status_code=404, detail="Member not found in project")

        if target_role == "owner" and actor_role != "owner":
            raise HTTPException(status_code=403, detail="Only owners can modify an owner's role")

        if new_role == "owner" and actor_role != "owner":
            raise HTTPException(status_code=403, detail="Only owners can promote to owner")

        if target_role == "owner" and new_role != "owner":
            # Demoting an owner
            owners_count = self._authz.count_owners(project_id)
            if owners_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot demote the last owner of the project")

        self._authz.update_member_role(project_id, target_user_id, new_role)
        target_user = self._user_repo.get_by_user_id(target_user_id)
        email = target_user.email if target_user else "unknown"
        return {"user_id": target_user_id, "email": email, "role": new_role}

    def remove_member(self, project_id: str, target_user_id: str, actor_role: str) -> None:
        target_role = self._authz.get_role(project_id, target_user_id)
        if not target_role:
            raise HTTPException(status_code=404, detail="Member not found in project")

        if target_role == "owner" and actor_role != "owner":
            raise HTTPException(status_code=403, detail="Only owners can remove an owner")

        if target_role == "owner":
            owners_count = self._authz.count_owners(project_id)
            if owners_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove the last owner of the project")

        self._authz.remove_member(project_id, target_user_id)

    # API Key Management
    def _hash_secret(self, secret: str) -> str:
        return hashlib.sha256(secret.encode('utf-8')).hexdigest()

    def create_api_key(self, project_id: str, name: str, user_id: str) -> dict:
        key_id = secrets.token_hex(4)
        secret = secrets.token_hex(16)
        full_key = f"pk_live_{key_id}_{secret}"

        secret_hash = self._hash_secret(secret)
        self._authz.create_api_key(key_id, project_id, name, secret_hash, user_id)
        return {"key_id": key_id, "key": full_key, "name": name}

    def list_api_keys(self, project_id: str) -> list[dict]:
        keys = self._authz.get_api_keys(project_id)
        # Format created_at to string if it's a datetime, but SQLite driver might return str or datetime.
        for k in keys:
            if not isinstance(k["created_at"], str):
                k["created_at"] = str(k["created_at"])
        return keys

    def revoke_api_key(self, project_id: str, key_id: str) -> None:
        key = self._authz.get_api_key(key_id)
        if not key or key["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="API key not found")
        self._authz.revoke_api_key(project_id, key_id)

    def rotate_api_key(self, project_id: str, key_id: str, user_id: str) -> dict:
        key = self._authz.get_api_key(key_id)
        if not key or key["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="API key not found")

        name = key["name"]
        self._authz.revoke_api_key(project_id, key_id)
        return self.create_api_key(project_id, name, user_id)

    # Table Management (Control Plane)
    def create_table(self, project_id: str, table_name: str, columns: dict[str, str]) -> None:
        if not self._tenant_db: return
        self._tenant_db.create_table(project_id, table_name, columns)

    def list_tables(self, project_id: str) -> list[str]:
        if not self._tenant_db: return []
        return self._tenant_db.list_tables(project_id)

    def get_table_schema(self, project_id: str, table_name: str) -> list[dict]:
        if not self._tenant_db: return []
        return self._tenant_db.get_table_schema(project_id, table_name)

    def delete_table(self, project_id: str, table_name: str) -> None:
        if not self._tenant_db: return
        self._tenant_db.delete_table(project_id, table_name)

    # Data CRUD (Data Plane)
    def insert_row(self, project_id: str, table_name: str, data: dict) -> str:
        if not self._tenant_db: return ""
        return self._tenant_db.insert_row(project_id, table_name, data)

    def get_row(self, project_id: str, table_name: str, row_id: str) -> dict:
        if not self._tenant_db: return None
        row = self._tenant_db.get_row(project_id, table_name, row_id)
        if not row:
            raise HTTPException(status_code=404, detail="Row not found")
        return row

    def list_rows(self, project_id: str, table_name: str, limit: int = 100, offset: int = 0) -> list[dict]:
        if not self._tenant_db: return []
        return self._tenant_db.list_rows(project_id, table_name, limit, offset)

    def update_row(self, project_id: str, table_name: str, row_id: str, data: dict) -> None:
        if not self._tenant_db: return
        updated = self._tenant_db.update_row(project_id, table_name, row_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="Row not found")

    def delete_row(self, project_id: str, table_name: str, row_id: str) -> None:
        if not self._tenant_db: return
        deleted = self._tenant_db.delete_row(project_id, table_name, row_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Row not found")
