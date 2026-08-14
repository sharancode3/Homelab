from __future__ import annotations
from app.storage.providers.sqlite import SQLiteProjectRepository, SQLiteAuditRepository, SQLiteOperationHistoryRepository

import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone
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


# Mock project_registry module
if "app.project_registry" not in sys.modules:
    project_registry_module = types.ModuleType("app.project_registry")
    project_registry_module.ProjectRegistryEntry = ProjectRegistryEntry
    project_registry_module.ProjectType = ProjectType
    project_registry_module.ProjectStatus = ProjectStatus
    sys.modules["app.project_registry"] = project_registry_module

from app.platform.health.engine import HealthEngine
from app.platform.health.enums import HealthCategory, HealthSeverity, HealthState, HealthStatus
from app.platform.health.models import HealthIndicator
from app.platform.lifecycle import LifecycleManager
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


class HealthEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ProjectRegistryManager(SQLiteProjectRepository())
        self.project = build_project()
        self.registry.register(self.project)
        self.lifecycle = LifecycleManager(self.registry)
        self.lifecycle.register(self.project.project_id)
        self.engine = HealthEngine(self.registry, self.lifecycle)

    def test_healthy_result(self) -> None:
        snapshot = self.engine.evaluate(self.project.project_id)

        self.assertTrue(snapshot.success)
        self.assertEqual(snapshot.status, HealthStatus.COMPLETED)
        self.assertEqual(snapshot.state, HealthState.HEALTHY)
        self.assertEqual(snapshot.project_id, self.project.project_id)

    def test_degraded_result(self) -> None:
        # Mock _collect_indicators to return a degraded indicator
        def mock_collect_indicators(project_id: str) -> tuple[HealthIndicator, ...]:
            return (
                HealthIndicator(
                    indicator_id="api_1",
                    name="API Latency",
                    category=HealthCategory.API,
                    state=HealthState.DEGRADED,
                    severity=HealthSeverity.WARNING,
                    details={},
                    checked_at=datetime.now(timezone.utc),
                ),
            )
        
        self.engine._collect_indicators = mock_collect_indicators  # type: ignore[method-assign]
        snapshot = self.engine.evaluate(self.project.project_id)
        
        self.assertTrue(snapshot.success)
        self.assertEqual(snapshot.state, HealthState.DEGRADED)

    def test_unhealthy_result(self) -> None:
        def mock_collect_indicators(project_id: str) -> tuple[HealthIndicator, ...]:
            return (
                HealthIndicator(
                    indicator_id="api_1",
                    name="API Latency",
                    category=HealthCategory.API,
                    state=HealthState.DEGRADED,
                    severity=HealthSeverity.WARNING,
                    details={},
                    checked_at=datetime.now(timezone.utc),
                ),
                HealthIndicator(
                    indicator_id="db_1",
                    name="Database Connectivity",
                    category=HealthCategory.DATABASE,
                    state=HealthState.UNHEALTHY,
                    severity=HealthSeverity.CRITICAL,
                    details={},
                    checked_at=datetime.now(timezone.utc),
                ),
            )
        
        self.engine._collect_indicators = mock_collect_indicators  # type: ignore[method-assign]
        snapshot = self.engine.evaluate(self.project.project_id)
        
        self.assertTrue(snapshot.success)
        self.assertEqual(snapshot.state, HealthState.UNHEALTHY)

    def test_unknown_target(self) -> None:
        snapshot = self.engine.evaluate("proj_9999")
        
        self.assertFalse(snapshot.success)
        self.assertEqual(snapshot.status, HealthStatus.FAILED)
        self.assertEqual(snapshot.state, HealthState.UNKNOWN)
        self.assertIn("Unknown project", snapshot.message)

    def test_indicator_aggregation(self) -> None:
        def mock_collect_indicators(project_id: str) -> tuple[HealthIndicator, ...]:
            return ()
            
        self.engine._collect_indicators = mock_collect_indicators  # type: ignore[method-assign]
        snapshot = self.engine.evaluate(self.project.project_id)
        
        self.assertTrue(snapshot.success)
        self.assertEqual(snapshot.state, HealthState.UNKNOWN)

    def test_snapshot_generation(self) -> None:
        snapshot = self.engine.evaluate(self.project.project_id)
        
        self.assertIsNotNone(snapshot.evaluated_at)
        self.assertEqual(snapshot.project_slug, "internloom")
        self.assertEqual(snapshot.project_name, "InternLoom")
        self.assertTrue(len(snapshot.indicators) > 0)


if __name__ == "__main__":
    unittest.main()
