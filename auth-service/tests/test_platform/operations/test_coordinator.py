from app.storage.providers.sqlite import SQLiteProjectRepository, SQLiteAuditRepository, SQLiteOperationHistoryRepository
import sys
import types
from dataclasses import dataclass
from enum import Enum
import unittest
from typing import Any

from app.platform.audit.engine import AuditEngine
from app.platform.backup.engine import BackupEngine
from app.platform.deployment.engine import DeploymentEngine
from app.platform.events.engine import EventEngine
from app.platform.health.engine import HealthEngine
from app.platform.lifecycle.manager import LifecycleManager
from app.platform.operations.coordinator import PlatformOperationsCoordinator
from app.platform.operations.enums import OperationStatus, OperationType
from app.platform.restore.engine import RestoreEngine
from app.platform.validation.engine import ValidationEngine
from app.project_registry_manager import ProjectRegistryManager

class ProjectType(str, Enum):
    BACKEND = "backend"

class ProjectStatus(str, Enum):
    ACTIVE = "active"

@dataclass(slots=True)
class ProjectRegistryEntry:
    project_id: str
    project_name: str
    project_slug: str
    project_type: ProjectType
    status: ProjectStatus
    project_version: str | None = "1.0.0"

if "app.project_registry" not in sys.modules:
    project_registry_module = types.ModuleType("app.project_registry")
    project_registry_module.ProjectRegistryEntry = ProjectRegistryEntry
    project_registry_module.ProjectType = ProjectType
    project_registry_module.ProjectStatus = ProjectStatus
    sys.modules["app.project_registry"] = project_registry_module


def build_project() -> ProjectRegistryEntry:
    return ProjectRegistryEntry(
        project_id="proj_0001",
        project_name="InternLoom",
        project_slug="internloom",
        project_type=ProjectType.BACKEND,
        status=ProjectStatus.ACTIVE,
        project_version="1.0.0",
    )

class MockEngineResult:
    def __init__(self, success: bool, message: str = ""):
        self.success = success
        self.message = message

class PlatformOperationsCoordinatorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ProjectRegistryManager(SQLiteProjectRepository())
        self.project = build_project()
        self.registry.register(self.project)
        
        self.lifecycle = LifecycleManager(self.registry)
        self.lifecycle.register(self.project.project_id)
        
        self.validation = ValidationEngine(self.registry, self.lifecycle)
        
        self.deployment = DeploymentEngine(self.registry, self.lifecycle, self.validation)
        self.backup = BackupEngine(self.registry, self.lifecycle)
        self.restore = RestoreEngine(self.registry, self.lifecycle, self.validation)
        self.health = HealthEngine(self.registry, self.lifecycle)
        self.events = EventEngine()
        self.audit = AuditEngine(SQLiteAuditRepository())
        
        self.coordinator = PlatformOperationsCoordinator(
            lifecycle_manager=self.lifecycle,
            validation_engine=self.validation,
            deployment_engine=self.deployment,
            backup_engine=self.backup,
            restore_engine=self.restore,
            health_engine=self.health,
            event_engine=self.events,
            audit_engine=self.audit,
            history_repository=SQLiteOperationHistoryRepository(),
        )

    def test_successful_operation_flow(self) -> None:
        # Mock deployment to return success to avoid full deployment pipeline running
        self.deployment.deploy = lambda **kwargs: MockEngineResult(True, "Success")  # type: ignore[method-assign]
        
        result = self.coordinator.execute_operation(
            project_id=self.project.project_id,
            operation_type=OperationType.DEPLOY
        )
        
        self.assertEqual(result.status, OperationStatus.COMPLETED)
        self.assertIn("deploy", result.completed_steps)
        self.assertEqual(len(result.failures), 0)

    def test_duplicate_operation_prevention(self) -> None:
        # Simulate active lock
        self.coordinator._acquire_lock(self.project.project_id, "op_test")
        
        result = self.coordinator.execute_operation(
            project_id=self.project.project_id,
            operation_type=OperationType.DEPLOY
        )
        
        self.assertEqual(result.status, OperationStatus.FAILED)
        self.assertIn("already has an active operation", result.failures[0])
        
        # Cleanup
        self.coordinator._release_lock(self.project.project_id, "op_test")

    def test_engine_failure_handling(self) -> None:
        self.deployment.deploy = lambda **kwargs: MockEngineResult(False, "Failed to deploy")  # type: ignore[method-assign]
        
        result = self.coordinator.execute_operation(
            project_id=self.project.project_id,
            operation_type=OperationType.DEPLOY
        )
        
        self.assertEqual(result.status, OperationStatus.FAILED)
        self.assertIn("deploy", result.completed_steps)
        self.assertIn("Failed to deploy", result.failures)

    def test_event_and_audit_creation(self) -> None:
        self.backup.backup = lambda **kwargs: MockEngineResult(True, "Backup Success")  # type: ignore[method-assign]
        
        result = self.coordinator.execute_operation(
            project_id=self.project.project_id,
            operation_type=OperationType.BACKUP
        )
        
        self.assertEqual(result.status, OperationStatus.COMPLETED)
        
        # Check audit
        records = self.audit.query(project_id=self.project.project_id)
        self.assertGreaterEqual(len(records), 1)
        self.assertTrue(any(r.event_type == "operation_backup" for r in records))
        
        # Check events (EventEngine records published events)
        event_types = [e.event_type for e in self.events._recorded_events.values()]
        self.assertIn("backup_started", event_types)
        self.assertIn("backup_completed", event_types)

if __name__ == "__main__":
    unittest.main()
