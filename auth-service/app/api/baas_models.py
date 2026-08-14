from enum import Enum
from pydantic import BaseModel, Field

class ProjectRole(str, Enum):
    owner = "owner"
    admin = "admin"
    developer = "developer"
    viewer = "viewer"

class BaaSProjectCreateRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=100)
    project_slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    project_type: str = "backend"
    project_version: str = "1.0.0"

class BaaSProjectResponse(BaseModel):
    project_id: str
    project_name: str
    project_slug: str
    project_type: str
    status: str
    project_version: str | None = None

class ProjectMemberResponse(BaseModel):
    user_id: str
    email: str
    role: ProjectRole

class AddMemberRequest(BaseModel):
    email: str
    role: ProjectRole

class UpdateMemberRoleRequest(BaseModel):
    role: ProjectRole

class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class ApiKeyResponse(BaseModel):
    key_id: str
    key: str  # Only returned on creation
    name: str

class ApiKeyListResponse(BaseModel):
    key_id: str
    name: str
    created_at: str
    is_active: bool

class TableColumnDef(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")
    type: str

class TableCreateRequest(BaseModel):
    name: str = Field(..., pattern=r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$')
    columns: dict[str, str]

class TableResponse(BaseModel):
    name: str

class RowCreateResponse(BaseModel):
    id: str

class RowResponse(BaseModel):
    data: dict
