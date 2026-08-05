from __future__ import annotations
from app.storage.providers.sqlite import SQLiteProjectRepository, SQLiteAuditRepository, SQLiteOperationHistoryRepository

import sys
import types
from dataclasses import dataclass
from enum import Enum


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
    project_version: str | None = None


project_registry_module = types.ModuleType("app.project_registry")
project_registry_module.ProjectRegistryEntry = ProjectRegistryEntry
project_registry_module.ProjectType = ProjectType
project_registry_module.ProjectStatus = ProjectStatus
sys.modules["app.project_registry"] = project_registry_module

import unittest

from app.platform.lifecycle import LifecycleManager
from app.platform.lifecycle.enums import LifecycleOperation, LifecycleState
from app.platform.validation import ValidationEngine, ValidationStatus
from app.project_registry_manager import ProjectRegistryManager


def build_project(
    project_id: str = "proj_0001",
    project_version: str | None = "1.0.0",
) -> ProjectRegistryEntry:
    return ProjectRegistryEntry(
        project_id=project_id,
        project_name="InternLoom",
        project_slug="internloom",
        project_type=ProjectType.BACKEND,
        status=ProjectStatus.ACTIVE,
        project_version=project_version,
    )


class ValidationEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ProjectRegistryManager(SQLiteProjectRepository())
        self.lifecycle = LifecycleManager(self.registry)

    def test_successful_validation(self) -> None:
        project = build_project()
        self.registry.register(project)
        self.lifecycle.register(project.project_id)

        engine = ValidationEngine(self.registry, self.lifecycle)
        result = engine.validate(project.project_id, LifecycleOperation.VALIDATE)

        self.assertEqual(result.status, ValidationStatus.VALID)
        self.assertEqual(result.issues, ())

    def test_warning_only_validation(self) -> None:
        project = build_project(project_version=None)
        self.registry.register(project)
        self.lifecycle.register(project.project_id)

        engine = ValidationEngine(self.registry, self.lifecycle)
        result = engine.validate(project.project_id, LifecycleOperation.VALIDATE)

        self.assertEqual(result.status, ValidationStatus.WARNING)
        self.assertEqual(len(result.warnings), 1)

    def test_invalid_validation(self) -> None:
        project = build_project(project_version="1.0.0")
        self.registry.register(project)
        self.lifecycle.register(project.project_id)

        engine = ValidationEngine(self.registry, self.lifecycle)
        result = engine.validate(project.project_id, LifecycleOperation.DEPLOY)

        self.assertEqual(result.status, ValidationStatus.INVALID)
        self.assertGreaterEqual(len(result.invalid_issues), 1)

    def test_unknown_project(self) -> None:
        engine = ValidationEngine(self.registry, self.lifecycle)
        result = engine.validate("proj_9999", LifecycleOperation.VALIDATE)

        self.assertEqual(result.status, ValidationStatus.INVALID)
        self.assertTrue(any(issue.validation_id == "REG001" for issue in result.issues))

    def test_invalid_lifecycle_state(self) -> None:
        project = build_project()
        self.registry.register(project)
        self.lifecycle.register(project.project_id)
        self.lifecycle.fail(project.project_id)

        engine = ValidationEngine(self.registry, self.lifecycle)
        result = engine.validate(project.project_id, LifecycleOperation.START)

        self.assertEqual(result.status, ValidationStatus.INVALID)
        self.assertTrue(any(issue.validation_id == "LIFE002" for issue in result.issues))

    def test_aggregation_behavior(self) -> None:
        project = build_project(project_version=None)
        self.registry.register(project)
        self.lifecycle.register(project.project_id)
        self.lifecycle.fail(project.project_id)

        engine = ValidationEngine(self.registry, self.lifecycle)
        result = engine.validate(project.project_id, LifecycleOperation.START)

        self.assertEqual(result.status, ValidationStatus.INVALID)
        self.assertEqual(len(result.warnings), 1)
        self.assertGreaterEqual(len(result.invalid_issues), 1)


if __name__ == "__main__":
    unittest.main()
