from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ProjectType(str, Enum):
    BACKEND = "backend"
    AI = "ai"
    API = "api"
    WORKER = "worker"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ProjectRegistryEntry(BaseModel):
    project_id: str = Field(
        min_length=9,
        pattern=r"^proj_\d{4,}$",
        max_length=20,
        description="Unique project identifier",
    )
    project_name: str = Field(
        min_length=1,
        max_length=100,
        description="Human-readable project name",
    )
    project_slug: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Canonical lowercase project slug",
    )
    project_type: ProjectType = Field(description="Project category")
    status: ProjectStatus = Field(description="Current project lifecycle status")

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional project summary",
    )
    public_hostname: str | None = Field(default=None, description="Public hostname for Caddy routing")
    database_name: str | None = Field(default=None, description="Project database name")
    bucket_name: str | None = Field(default=None, description="Project MinIO bucket name")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Entry creation timestamp in UTC",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Entry update timestamp in UTC",
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Optional project labels",
    )
    project_version: str | None = Field(
        default=None,
        pattern=r"^\d+\.\d+\.\d+(?:-[A-Za-z0-9]+)?$",
        description="Deployed project version",
    )