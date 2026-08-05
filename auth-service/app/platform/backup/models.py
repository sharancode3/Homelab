from dataclasses import dataclass
from datetime import datetime

from app.platform.backup.enums import BackupStage, BackupStatus, BackupType


@dataclass(frozen=True, slots=True)
class BackupPlan:
    project_id: str
    project_slug: str
    project_name: str
    backup_type: BackupType
    requested_by: str | None
    status: BackupStatus
    ordered_stages: tuple[BackupStage, ...]
    dependencies: tuple[str, ...]
    timeout_seconds: int
    retry_count: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class BackupManifest:
    manifest_version: str
    backup_id: str
    project_id: str
    project_slug: str
    project_name: str
    project_version: str | None
    backup_type: BackupType
    files_included: tuple[str, ...]
    checksums: tuple[tuple[str, str], ...]
    created_at: datetime
    engine_version: str


@dataclass(frozen=True, slots=True)
class BackupMetadata:
    backup_id: str
    project_id: str
    project_slug: str
    project_name: str
    project_version: str | None
    backup_type: BackupType
    status: BackupStatus
    manifest_version: str
    manifest_checksum: str
    artifact_reference: str
    engine_version: str
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class BackupResult:
    project_id: str
    project_slug: str
    project_name: str
    backup_type: BackupType
    status: BackupStatus
    plan: BackupPlan
    manifest: BackupManifest | None
    metadata: BackupMetadata | None
    artifact_reference: str | None
    executed_stages: tuple[BackupStage, ...]
    verification_passed: bool
    success: bool
    message: str
    started_at: datetime
    completed_at: datetime
    failure_reason: str | None = None
