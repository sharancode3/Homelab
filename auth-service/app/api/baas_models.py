from pydantic import BaseModel, Field

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
