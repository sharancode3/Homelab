import sys
import types
from dataclasses import dataclass
from enum import Enum
import unittest

from app.platform.audit.engine import AuditEngine
from app.platform.backup.engine import BackupEngine
from app.platform.deployment.engine import DeploymentEngine
from app.platform.events.engine import EventEngine
from app.platform.health.engine import HealthEngine
from app.platform.lifecycle.manager import LifecycleManager
from app.platform.lifecycle.enums import LifecycleOperation
from app.platform.operations.coordinator import PlatformOperationsCoordinator
from app.platform.operations.enums import OperationStatus, OperationType
from app.platform.restore.engine import RestoreEngine
from app.platform.validation.engine import ValidationEngine
from app.platform.validation.models import ValidationIssue
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
        project_id="proj_integration_1",
        project_name="IntegrationProject",
        project_slug="integration-project",
        project_type=ProjectType.BACKEND,
        status=ProjectStatus.ACTIVE,
        project_version="1.0.0",
    )

class MockEngineResult:
    def __init__(self, success: bool, message: str = ""):
        self.success = success
        self.message = message

class PlatformIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ProjectRegistryManager()
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
        self.audit = AuditEngine()
        
        self.coordinator = PlatformOperationsCoordinator(
            lifecycle_manager=self.lifecycle,
            validation_engine=self.validation,
            deployment_engine=self.deployment,
            backup_engine=self.backup,
            restore_engine=self.restore,
            health_engine=self.health,
            event_engine=self.events,
            audit_engine=self.audit,
        )

    def test_end_to_end_deploy(self) -> None:
        # Mock deployment logic specifically so we don't need real infrastructure
        self.deployment.deploy = lambda **kwargs: MockEngineResult(True, "Deployed")  # type: ignore[method-assign]

        # Trigger operation via coordinator
        result = self.coordinator.execute_operation(
            project_id=self.project.project_id,
            operation_type=OperationType.DEPLOY
        )
        
        self.assertEqual(result.status, OperationStatus.COMPLETED)
        
        # Verify Audit was recorded
        audits = self.audit.query(project_id=self.project.project_id)
        self.assertTrue(any(a.event_type == "operation_deploy" for a in audits))
        
        # Verify Events were published
        published_events = [e.event_type for e in self.events._recorded_events.values()]
        self.assertIn("deploy_started", published_events)
        self.assertIn("deploy_completed", published_events)
        
    def test_validation_blocking_operation(self) -> None:
        # Cause validation to block the deployment by failing a transition early
        self.deployment.deploy = lambda **kwargs: MockEngineResult(False, "Validation failed: Invalid transition from START to DEPLOY")  # type: ignore[method-assign]
        
        result = self.coordinator.execute_operation(
            project_id=self.project.project_id,
            operation_type=OperationType.DEPLOY
        )
        
        self.assertEqual(result.status, OperationStatus.FAILED)
        self.assertIn("Validation failed", result.failures[0])
        
        # Verify Audit recorded the failure
        audits = self.audit.query(project_id=self.project.project_id)
        self.assertTrue(any(a.outcome_status.value == "failure" for a in audits))
        
        # Verify Event published the failure
        published_events = [e.event_type for e in self.events._recorded_events.values()]
        self.assertIn("deploy_failed", published_events)

if __name__ == "__main__":
    unittest.main()
