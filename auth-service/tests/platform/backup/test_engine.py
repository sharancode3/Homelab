from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from enum import Enum

import unittest


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


@dataclass(slots=True)
class ProjectRegistryEntry:
    project_id: str
    project_name: str
    project_slug: str
    project_type: ProjectType
    status: ProjectStatus
    project_version: str | None = "1.0.0"


project_registry_module = types.ModuleType("app.project_registry")
project_registry_module.ProjectRegistryEntry = ProjectRegistryEntry
project_registry_module.ProjectType = ProjectType
project_registry_module.ProjectStatus = ProjectStatus
sys.modules["app.project_registry"] = project_registry_module

from app.platform.backup import (
    BackupEngine,
    BackupStatus,
    BackupType,
    BackupVerificationError,
)
from app.platform.lifecycle import LifecycleManager
from app.platform.lifecycle.enums import LifecycleState
from app.project_registry_manager import ProjectRegistryManager


def build_project() -> ProjectRegistryEntry:
    return ProjectRegistryEntry(
        project_id="proj_0001",
        project_name="InternLoom",
        project_slug="internloom",
        project_type=ProjectType.BACKEND,
        status=ProjectStatus.ACTIVE,
        project_version="1.0.0",
    )


class BackupEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ProjectRegistryManager()
        self.project = build_project()
        self.registry.register(self.project)
        self.lifecycle = LifecycleManager(self.registry)
        self.lifecycle.register(self.project.project_id)
        self.engine = BackupEngine(self.registry, self.lifecycle)

    def test_successful_backup(self) -> None:
        result = self.engine.backup(self.project.project_id)

        self.assertTrue(result.success)
        self.assertEqual(result.status, BackupStatus.COMPLETED)
        self.assertIsNotNone(result.manifest)
        self.assertIsNotNone(result.metadata)
        self.assertTrue(result.verification_passed)

    def test_invalid_backup_request(self) -> None:
        with self.assertRaises(Exception):
            self.engine.create_plan("proj_9999")

    def test_manifest_generation(self) -> None:
        plan = self.engine.create_plan(self.project.project_id, BackupType.FULL)
        manifest = self.engine.create_manifest(plan)

        self.assertEqual(manifest.project_id, self.project.project_id)
        self.assertEqual(manifest.backup_type, BackupType.FULL)
        self.assertGreater(len(manifest.files_included), 0)

    def test_metadata_generation(self) -> None:
        plan = self.engine.create_plan(self.project.project_id)
        manifest = self.engine.create_manifest(plan)
        metadata = self.engine.generate_metadata(plan, manifest, "artifact_test")

        self.assertEqual(metadata.backup_id, manifest.backup_id)
        self.assertEqual(metadata.artifact_reference, "artifact_test")
        self.assertEqual(metadata.status, BackupStatus.MANIFEST_CREATED)

    def test_verification_failure(self) -> None:
        engine = BackupEngine(self.registry, self.lifecycle)
        engine._verify_manifest_integrity = lambda manifest: False  # type: ignore[method-assign]

        result = engine.backup(self.project.project_id)

        self.assertFalse(result.success)
        self.assertEqual(result.status, BackupStatus.FAILED)
        self.assertFalse(result.verification_passed)

    def test_backup_result_aggregation(self) -> None:
        result = self.engine.backup(self.project.project_id)

        self.assertEqual(result.plan.project_id, self.project.project_id)
        self.assertEqual(result.metadata.backup_id, result.manifest.backup_id)
        self.assertEqual(result.executed_stages[-1].value, "finalization")


if __name__ == "__main__":
    unittest.main()
