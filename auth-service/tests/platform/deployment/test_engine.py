from __future__ import annotations

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
    project_version: str | None = "1.0.0"


project_registry_module = types.ModuleType("app.project_registry")
project_registry_module.ProjectRegistryEntry = ProjectRegistryEntry
project_registry_module.ProjectType = ProjectType
project_registry_module.ProjectStatus = ProjectStatus
sys.modules["app.project_registry"] = project_registry_module

import unittest

from app.platform.deployment import (
    DeploymentEngine,
    DeploymentStage,
    DeploymentStatus,
    DeploymentVerificationError,
)
from app.platform.lifecycle import LifecycleManager
from app.platform.lifecycle.enums import LifecycleOperation
from app.platform.validation import ValidationEngine
from app.platform.validation.enums import ValidationStatus
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


class DeploymentEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ProjectRegistryManager()
        self.project = build_project()
        self.registry.register(self.project)
        self.lifecycle = LifecycleManager(self.registry)
        self.lifecycle.register(self.project.project_id)
        self.lifecycle.validate(self.project.project_id)
        self.validation = ValidationEngine(self.registry, self.lifecycle)
        self.engine = DeploymentEngine(
            self.registry, self.lifecycle, self.validation
        )

    def test_deployment_plan_generation(self) -> None:
        plan = self.engine.create_plan(self.project.project_id)

        self.assertEqual(plan.project_id, self.project.project_id)
        self.assertEqual(plan.status, DeploymentStatus.PLANNED)
        self.assertEqual(
            plan.ordered_stages,
            (
                DeploymentStage.REQUEST_VALIDATION,
                DeploymentStage.PREPARATION,
                DeploymentStage.EXECUTION,
                DeploymentStage.VERIFICATION,
                DeploymentStage.FINALIZATION,
            ),
        )

    def test_successful_deployment(self) -> None:
        result = self.engine.deploy(self.project.project_id)

        self.assertTrue(result.success)
        self.assertEqual(result.status, DeploymentStatus.COMPLETED)
        self.assertTrue(result.verification_passed)
        self.assertIn(DeploymentStage.VERIFICATION, result.executed_stages)

    def test_invalid_deployment_request(self) -> None:
        invalid_registry = ProjectRegistryManager()
        project = build_project()
        invalid_registry.register(project)
        lifecycle = LifecycleManager(invalid_registry)
        lifecycle.register(project.project_id)
        validation = ValidationEngine(invalid_registry, lifecycle)
        engine = DeploymentEngine(invalid_registry, lifecycle, validation)

        with self.assertRaises(Exception):
            engine.create_plan(project.project_id)

    def test_failed_deployment(self) -> None:
        engine = DeploymentEngine(self.registry, self.lifecycle, self.validation)
        engine._execute_stage = lambda stage, plan: None  # type: ignore[method-assign]
        engine._verify_deployment = lambda plan, stages: False  # type: ignore[method-assign]

        result = engine.deploy(self.project.project_id)

        self.assertFalse(result.success)
        self.assertEqual(result.status, DeploymentStatus.FAILED)
        self.assertFalse(result.verification_passed)

    def test_deployment_verification(self) -> None:
        plan = self.engine.create_plan(self.project.project_id)
        self.assertTrue(self.engine.verify(plan))

    def test_deployment_result_aggregation(self) -> None:
        result = self.engine.deploy(self.project.project_id)

        self.assertEqual(result.plan.project_id, self.project.project_id)
        self.assertEqual(result.executed_stages[-1], DeploymentStage.FINALIZATION)


if __name__ == "__main__":
    unittest.main()
