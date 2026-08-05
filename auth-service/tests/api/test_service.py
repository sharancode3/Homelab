import unittest
from unittest.mock import MagicMock

from app.api.models import ProjectRegisterRequest
from app.api.service import APIServiceLayer
from app.platform.health.engine import HealthEngine
from app.platform.lifecycle.manager import LifecycleManager
from app.platform.lifecycle.exceptions import LifecycleConflictError
from app.platform.operations.coordinator import PlatformOperationsCoordinator
from app.platform.validation.engine import ValidationEngine
from app.project_registry_manager import ProjectRegistryManager


class APIServiceLayerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_registry = MagicMock(spec=ProjectRegistryManager)
        self.mock_lifecycle = MagicMock(spec=LifecycleManager)
        self.mock_validation = MagicMock(spec=ValidationEngine)
        self.mock_health = MagicMock(spec=HealthEngine)
        self.mock_coordinator = MagicMock(spec=PlatformOperationsCoordinator)

        self.service = APIServiceLayer(
            registry=self.mock_registry,
            lifecycle=self.mock_lifecycle,
            validation=self.mock_validation,
            health=self.mock_health,
            coordinator=self.mock_coordinator,
        )

    def test_register_project_creates_lifecycle_state(self) -> None:
        """Test that registering a project also registers it in the lifecycle manager."""
        req = ProjectRegisterRequest(
            project_id="proj_1",
            project_name="Test Project",
            project_slug="test-project",
        )
        
        response = self.service.register_project(req)
        
        self.assertEqual(response.status, "success")
        self.mock_registry.register.assert_called_once()
        self.mock_lifecycle.register.assert_called_once_with("proj_1")

    def test_register_project_ignores_duplicate_lifecycle_safely(self) -> None:
        """Test that a duplicate lifecycle error during registration is handled safely."""
        self.mock_lifecycle.register.side_effect = LifecycleConflictError("already registered")
        
        req = ProjectRegisterRequest(
            project_id="proj_2",
            project_name="Duplicate Test",
            project_slug="duplicate-test",
        )
        
        # This should not raise an exception
        response = self.service.register_project(req)
        
        self.assertEqual(response.status, "success")
        self.mock_registry.register.assert_called_once()
        self.mock_lifecycle.register.assert_called_once_with("proj_2")


    def test_validate_project_advances_lifecycle(self) -> None:
        """Test that validating a project also advances its lifecycle state."""
        # Setup mock validation response
        mock_val_result = MagicMock()
        mock_val_result.is_valid = True
        mock_val_result.issues = []
        self.mock_validation.validate.return_value = mock_val_result
        
        response = self.service.validate_project("proj_1")
        
        self.assertTrue(response.is_valid)
        self.mock_lifecycle.validate.assert_called_once_with("proj_1")
        self.mock_validation.validate.assert_called_once_with("proj_1", "deploy")

    def test_validate_project_ignores_duplicate_lifecycle_safely(self) -> None:
        """Test that validating a project already validated doesn't crash."""
        self.mock_lifecycle.validate.side_effect = LifecycleConflictError("already validated")
        
        mock_val_result = MagicMock()
        mock_val_result.is_valid = True
        mock_val_result.issues = []
        self.mock_validation.validate.return_value = mock_val_result
        
        # This should not raise an exception
        response = self.service.validate_project("proj_2")
        
        self.assertTrue(response.is_valid)
        self.mock_lifecycle.validate.assert_called_once_with("proj_2")
        self.mock_validation.validate.assert_called_once_with("proj_2", "deploy")


if __name__ == "__main__":
    unittest.main()
