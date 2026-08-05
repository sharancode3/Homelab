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


project_registry_module = types.ModuleType("app.project_registry")
project_registry_module.ProjectRegistryEntry = ProjectRegistryEntry
project_registry_module.ProjectType = ProjectType
project_registry_module.ProjectStatus = ProjectStatus
sys.modules["app.project_registry"] = project_registry_module

import unittest

from app.platform.lifecycle import (
    InvalidTransitionError,
    LifecycleConflictError,
    LifecycleManager,
    LifecycleState,
    ProjectNotFoundError,
)
from app.project_registry_manager import ProjectRegistryManager


def build_project(project_id: str = "proj_0001") -> ProjectRegistryEntry:
    return ProjectRegistryEntry(
        project_id=project_id,
        project_name="InternLoom",
        project_slug="internloom",
        project_type=ProjectType.BACKEND,
        status=ProjectStatus.ACTIVE,
    )


class LifecycleManagerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ProjectRegistryManager()
        self.project = build_project()
        self.registry.register(self.project)
        self.manager = LifecycleManager(self.registry)

    def test_valid_transitions(self) -> None:
        register_result = self.manager.register(self.project.project_id)
        self.assertEqual(register_result.current_state, LifecycleState.REGISTERED)

        validate_result = self.manager.validate(self.project.project_id)
        self.assertEqual(validate_result.current_state, LifecycleState.VALIDATED)

        deploy_result = self.manager.deploy(self.project.project_id)
        self.assertEqual(deploy_result.current_state, LifecycleState.DEPLOYED)

        start_result = self.manager.start(self.project.project_id)
        self.assertEqual(start_result.current_state, LifecycleState.RUNNING)

        stop_result = self.manager.stop(self.project.project_id)
        self.assertEqual(stop_result.current_state, LifecycleState.STOPPED)

    def test_archive(self) -> None:
        self.manager.register(self.project.project_id)
        self.manager.validate(self.project.project_id)
        self.manager.deploy(self.project.project_id)
        self.manager.start(self.project.project_id)
        self.manager.stop(self.project.project_id)

        archive_result = self.manager.archive(self.project.project_id)
        self.assertEqual(archive_result.current_state, LifecycleState.ARCHIVED)

    def test_fail(self) -> None:
        self.manager.register(self.project.project_id)
        self.manager.validate(self.project.project_id)
        self.manager.deploy(self.project.project_id)
        self.manager.start(self.project.project_id)

        fail_result = self.manager.fail(self.project.project_id)
        self.assertEqual(fail_result.current_state, LifecycleState.FAILED)

    def test_invalid_transition_raises(self) -> None:
        self.manager.register(self.project.project_id)

        with self.assertRaises(InvalidTransitionError):
            self.manager.deploy(self.project.project_id)

    def test_duplicate_operations_raise(self) -> None:
        self.manager.register(self.project.project_id)

        with self.assertRaises(LifecycleConflictError):
            self.manager.register(self.project.project_id)

        self.manager.validate(self.project.project_id)

        with self.assertRaises(LifecycleConflictError):
            self.manager.validate(self.project.project_id)

    def test_unknown_project_raises(self) -> None:
        with self.assertRaises(ProjectNotFoundError):
            self.manager.register("proj_9999")


if __name__ == "__main__":
    unittest.main()
