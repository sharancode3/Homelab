from __future__ import annotations
from app.storage.providers.sqlite import SQLiteProjectRepository, SQLiteAuditRepository, SQLiteOperationHistoryRepository

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


# We must redefine or reuse the mock project_registry if needed, but the previous test did this:
# (Since tests might run in isolation, we can safely recreate the mock module if it doesn't exist)
if "app.project_registry" not in sys.modules:
    project_registry_module = types.ModuleType("app.project_registry")
    project_registry_module.ProjectRegistryEntry = ProjectRegistryEntry
    project_registry_module.ProjectType = ProjectType
    project_registry_module.ProjectStatus = ProjectStatus
    sys.modules["app.project_registry"] = project_registry_module

from app.platform.lifecycle import LifecycleManager
from app.platform.restore.engine import RestoreEngine
from app.platform.restore.enums import RestoreStatus, RestoreType, RestoreMode
from app.platform.validation.engine import ValidationEngine
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


class RestoreEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ProjectRegistryManager(SQLiteProjectRepository())
        self.project = build_project()
        self.registry.register(self.project)
        self.lifecycle = LifecycleManager(self.registry)
        self.lifecycle.register(self.project.project_id)
        self.validation = ValidationEngine(self.registry, self.lifecycle)
        self.engine = RestoreEngine(self.registry, self.lifecycle, self.validation)

    def test_successful_restore(self) -> None:
        result = self.engine.restore(self.project.project_id, "bkp_123")

        self.assertTrue(result.success)
        self.assertEqual(result.status, RestoreStatus.COMPLETED)
        self.assertTrue(result.verification_passed)

    def test_invalid_restore_request_no_project(self) -> None:
        with self.assertRaises(Exception):
            self.engine.create_plan("proj_9999", "bkp_123")

    def test_invalid_restore_request_no_backup(self) -> None:
        with self.assertRaises(Exception):
            self.engine.create_plan(self.project.project_id, "")

    def test_verification_failure(self) -> None:
        engine = RestoreEngine(self.registry, self.lifecycle, self.validation)
        engine._verify_manifest = lambda backup_id: False  # type: ignore[method-assign]

        result = engine.restore(self.project.project_id, "bkp_123")

        self.assertFalse(result.success)
        self.assertEqual(result.status, RestoreStatus.FAILED)
        self.assertFalse(result.verification_passed)

    def test_restore_result_aggregation(self) -> None:
        result = self.engine.restore(self.project.project_id, "bkp_123")

        self.assertEqual(result.plan.project_id, self.project.project_id)
        self.assertEqual(result.executed_stages[-1].value, "finalization")


if __name__ == "__main__":
    unittest.main()
