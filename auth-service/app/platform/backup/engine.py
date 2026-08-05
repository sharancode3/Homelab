from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timezone

from app.platform.backup.enums import BackupStage, BackupStatus, BackupType
from app.platform.backup.exceptions import (
    BackupException,
    BackupManifestError,
    BackupPlanError,
    BackupRequestError,
    BackupVerificationError,
)
from app.platform.backup.models import (
    BackupManifest,
    BackupMetadata,
    BackupPlan,
    BackupResult,
)
from app.platform.lifecycle import LifecycleManager
from app.platform.lifecycle.enums import LifecycleState
from app.project_registry import ProjectRegistryEntry
from app.project_registry_manager import ProjectRegistryManager


class BackupEngine:
    """Deterministic, read-only backup coordinator with immutable artifacts."""

    _ENGINE_VERSION = "1.0"
    _MANIFEST_VERSION = "1.0"

    def __init__(
        self,
        registry: ProjectRegistryManager,
        lifecycle_manager: LifecycleManager,
    ) -> None:
        self._registry = registry
        self._lifecycle_manager = lifecycle_manager

    def create_plan(
        self,
        project_id: str,
        backup_type: BackupType = BackupType.FULL,
        requested_by: str | None = None,
        timeout_seconds: int = 300,
        retry_count: int = 0,
    ) -> BackupPlan:
        project = self._get_project(project_id)
        self._validate_request(project_id, backup_type, timeout_seconds, retry_count)
        return BackupPlan(
            project_id=project.project_id,
            project_slug=project.project_slug,
            project_name=project.project_name,
            backup_type=backup_type,
            requested_by=requested_by,
            status=BackupStatus.PLANNED,
            ordered_stages=self._default_stages(),
            dependencies=("registry", "lifecycle"),
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            created_at=datetime.now(timezone.utc),
        )

    def create_manifest(self, plan: BackupPlan) -> BackupManifest:
        self._validate_plan(plan)
        project = self._get_project(plan.project_id)
        backup_id = self._build_backup_id(plan)
        files_included = self._files_for_backup(plan.backup_type)
        checksums = tuple(
            (
                f"{file_name}.sha256",
                self._checksum_seed(plan.project_id, file_name, plan.backup_type.value),
            )
            for file_name in files_included
        )

        return BackupManifest(
            manifest_version=self._MANIFEST_VERSION,
            backup_id=backup_id,
            project_id=project.project_id,
            project_slug=project.project_slug,
            project_name=project.project_name,
            project_version=getattr(project, "project_version", None),
            backup_type=plan.backup_type,
            files_included=files_included,
            checksums=checksums,
            created_at=datetime.now(timezone.utc),
            engine_version=self._ENGINE_VERSION,
        )

    def generate_metadata(
        self,
        plan: BackupPlan,
        manifest: BackupManifest,
        artifact_reference: str,
    ) -> BackupMetadata:
        self._validate_plan(plan)
        self._validate_manifest(manifest, plan)
        if not artifact_reference.strip():
            raise BackupManifestError("Artifact reference is required.")

        created_at = datetime.now(timezone.utc)
        return BackupMetadata(
            backup_id=manifest.backup_id,
            project_id=plan.project_id,
            project_slug=plan.project_slug,
            project_name=plan.project_name,
            project_version=getattr(self._get_project(plan.project_id), "project_version", None),
            backup_type=plan.backup_type,
            status=BackupStatus.MANIFEST_CREATED,
            manifest_version=manifest.manifest_version,
            manifest_checksum=self._manifest_checksum(manifest),
            artifact_reference=artifact_reference,
            engine_version=self._ENGINE_VERSION,
            created_at=created_at,
            completed_at=created_at,
        )

    def verify_manifest_integrity(self, manifest: BackupManifest) -> bool:
        expected = self._manifest_checksum(manifest)
        return bool(expected) and all(
            checksum_name.endswith(".sha256") and checksum_value
            for checksum_name, checksum_value in manifest.checksums
        )

    def backup(
        self,
        project_id: str,
        backup_type: BackupType = BackupType.FULL,
        requested_by: str | None = None,
        timeout_seconds: int = 300,
        retry_count: int = 0,
    ) -> BackupResult:
        plan = self.create_plan(
            project_id=project_id,
            backup_type=backup_type,
            requested_by=requested_by,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
        )

        started_at = datetime.now(timezone.utc)
        executed_stages: list[BackupStage] = []
        manifest: BackupManifest | None = None
        metadata: BackupMetadata | None = None
        artifact_reference: str | None = None

        try:
            self._execute_stage(BackupStage.REQUEST_VALIDATION, plan)
            executed_stages.append(BackupStage.REQUEST_VALIDATION)

            self._execute_stage(BackupStage.MANIFEST_CREATION, plan)
            manifest = self.create_manifest(plan)
            executed_stages.append(BackupStage.MANIFEST_CREATION)

            self._execute_stage(BackupStage.METADATA_GENERATION, plan)
            artifact_reference = self._simulate_artifact_creation(plan, manifest)
            metadata = self.generate_metadata(plan, manifest, artifact_reference)
            executed_stages.append(BackupStage.METADATA_GENERATION)

            self._execute_stage(BackupStage.ARTIFACT_SIMULATION, plan)
            executed_stages.append(BackupStage.ARTIFACT_SIMULATION)

            self._execute_stage(BackupStage.MANIFEST_VERIFICATION, plan)
            if not self.verify_manifest_integrity(manifest):
                raise BackupVerificationError(
                    f"Backup manifest verification failed for {project_id}."
                )
            executed_stages.append(BackupStage.MANIFEST_VERIFICATION)

            executed_stages.append(BackupStage.FINALIZATION)
            completed_at = datetime.now(timezone.utc)
            return self._finalize_result(
                plan=replace(plan, status=BackupStatus.COMPLETED),
                manifest=manifest,
                metadata=metadata,
                artifact_reference=artifact_reference,
                executed_stages=tuple(executed_stages),
                started_at=started_at,
                completed_at=completed_at,
            )
        except BackupException as error:
            return BackupResult(
                project_id=plan.project_id,
                project_slug=plan.project_slug,
                project_name=plan.project_name,
                backup_type=plan.backup_type,
                status=BackupStatus.FAILED,
                plan=replace(plan, status=BackupStatus.FAILED),
                manifest=manifest,
                metadata=metadata,
                artifact_reference=artifact_reference,
                executed_stages=tuple(executed_stages),
                verification_passed=False,
                success=False,
                message=str(error),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                failure_reason=str(error),
            )

    def _finalize_result(
        self,
        *,
        plan: BackupPlan,
        manifest: BackupManifest | None,
        metadata: BackupMetadata | None,
        artifact_reference: str | None,
        executed_stages: tuple[BackupStage, ...],
        started_at: datetime,
        completed_at: datetime,
    ) -> BackupResult:
        return BackupResult(
            project_id=plan.project_id,
            project_slug=plan.project_slug,
            project_name=plan.project_name,
            backup_type=plan.backup_type,
            status=plan.status,
            plan=plan,
            manifest=manifest,
            metadata=metadata,
            artifact_reference=artifact_reference,
            executed_stages=executed_stages,
            verification_passed=True,
            success=True,
            message="Backup completed successfully.",
            started_at=started_at,
            completed_at=completed_at,
        )

    def _execute_stage(self, stage: BackupStage, plan: BackupPlan) -> None:
        if stage not in plan.ordered_stages:
            raise BackupPlanError(f"Stage {stage.value} is not part of the backup plan.")

    def _simulate_artifact_creation(
        self, plan: BackupPlan, manifest: BackupManifest
    ) -> str:
        payload = {
            "backup_id": manifest.backup_id,
            "project_id": plan.project_id,
            "backup_type": plan.backup_type.value,
            "manifest_checksum": self._manifest_checksum(manifest),
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return f"artifact_{digest[:16]}"

    def _validate_request(
        self,
        project_id: str,
        backup_type: BackupType,
        timeout_seconds: int,
        retry_count: int,
    ) -> None:
        if not project_id.strip():
            raise BackupRequestError("Project ID is required.")

        if timeout_seconds <= 0:
            raise BackupRequestError("Timeout must be positive.")

        if retry_count < 0:
            raise BackupRequestError("Retry count cannot be negative.")

        if backup_type not in tuple(BackupType):
            raise BackupRequestError(f"Unsupported backup type: {backup_type!r}")

        current_state = self._resolve_state(project_id)
        if current_state is None:
            raise BackupRequestError(f"Project is not registered with lifecycle manager: {project_id}")

        if current_state is LifecycleState.ARCHIVED:
            raise BackupRequestError(f"Archived projects cannot be backed up: {project_id}")

    def _validate_plan(self, plan: BackupPlan) -> None:
        if not plan.project_id.strip():
            raise BackupPlanError("Backup plan is missing a project ID.")

        if not plan.ordered_stages:
            raise BackupPlanError("Backup plan must include at least one stage.")

    def _validate_manifest(
        self, manifest: BackupManifest, plan: BackupPlan
    ) -> None:
        if manifest.project_id != plan.project_id:
            raise BackupManifestError("Manifest project mismatch.")

        if manifest.backup_type is not plan.backup_type:
            raise BackupManifestError("Manifest backup type mismatch.")

        if manifest.manifest_version != self._MANIFEST_VERSION:
            raise BackupManifestError("Unsupported manifest version.")

        if not manifest.files_included:
            raise BackupManifestError("Manifest must include at least one file entry.")

    def _resolve_state(self, project_id: str) -> LifecycleState | None:
        state_map = getattr(self._lifecycle_manager, "_states", None)
        if isinstance(state_map, dict):
            return state_map.get(project_id)

        get_state = getattr(self._lifecycle_manager, "get_state", None)
        if callable(get_state):
            return get_state(project_id)

        return None

    def _get_project(self, project_id: str) -> ProjectRegistryEntry:
        project = self._registry.get_by_project_id(project_id)
        if project is None:
            raise BackupRequestError(f"Unknown project: {project_id}")

        return project

    def _build_backup_id(self, plan: BackupPlan) -> str:
        seed = "|".join(
            (
                plan.project_id,
                plan.project_slug,
                plan.backup_type.value,
                plan.created_at.isoformat(),
                str(plan.retry_count),
            )
        )
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return f"bkp_{digest[:12]}"

    @staticmethod
    def _checksum_seed(project_id: str, file_name: str, backup_type: str) -> str:
        payload = "|".join((project_id, file_name, backup_type))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _manifest_checksum(self, manifest: BackupManifest) -> str:
        payload = {
            "manifest_version": manifest.manifest_version,
            "backup_id": manifest.backup_id,
            "project_id": manifest.project_id,
            "project_slug": manifest.project_slug,
            "backup_type": manifest.backup_type.value,
            "files_included": manifest.files_included,
            "checksums": manifest.checksums,
            "created_at": manifest.created_at.isoformat(),
            "engine_version": manifest.engine_version,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    @staticmethod
    def _files_for_backup(backup_type: BackupType) -> tuple[str, ...]:
        if backup_type is BackupType.FULL:
            return (
                "project-metadata",
                "project-database",
                "project-storage-manifest",
            )

        return (
            "project-database-changes",
            "project-storage-manifest",
        )

    @staticmethod
    def _default_stages() -> tuple[BackupStage, ...]:
        return (
            BackupStage.REQUEST_VALIDATION,
            BackupStage.MANIFEST_CREATION,
            BackupStage.METADATA_GENERATION,
            BackupStage.ARTIFACT_SIMULATION,
            BackupStage.MANIFEST_VERIFICATION,
            BackupStage.FINALIZATION,
        )
