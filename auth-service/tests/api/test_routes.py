import sys
import types
from dataclasses import dataclass
from enum import Enum
import unittest
from unittest.mock import MagicMock

from app.api.models import (
    BackupRequest,
    DeployRequest,
    HealthResponse,
    OperationResponse,
    ProjectRegisterRequest,
    ProjectRegisterResponse,
    RestoreRequest,
    ValidateResponse,
)
from app.api.routes import (
    register_project,
    validate_project,
    deploy_project,
    backup_project,
    restore_project,
    get_health,
)
from app.api.service import APIServiceLayer

class APIRoutesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_service = MagicMock(spec=APIServiceLayer)

    def test_register_project(self) -> None:
        self.mock_service.register_project.return_value = ProjectRegisterResponse(
            project_id="proj_1",
            status="success",
            message="Registered"
        )
        
        req = ProjectRegisterRequest(
            project_id="proj_1",
            project_name="Test Project",
            project_slug="test-project",
        )
        response = register_project(req=req, service=self.mock_service)
        
        self.assertEqual(response.project_id, "proj_1")
        self.assertEqual(response.status, "success")

    def test_validate_project(self) -> None:
        self.mock_service.validate_project.return_value = ValidateResponse(
            project_id="proj_1",
            is_valid=True,
            issues=[]
        )
        
        response = validate_project(project_id="proj_1", service=self.mock_service)
        
        self.assertTrue(response.is_valid)

    def test_deploy_project(self) -> None:
        self.mock_service.deploy_project.return_value = OperationResponse(
            operation_id="op_1",
            status="completed",
            completed_steps=["deploy"],
            failures=[]
        )
        
        req = DeployRequest(requested_by="admin")
        response = deploy_project(project_id="proj_1", req=req, service=self.mock_service)
        
        self.assertEqual(response.status, "completed")

    def test_backup_project(self) -> None:
        self.mock_service.backup_project.return_value = OperationResponse(
            operation_id="op_2",
            status="completed",
            completed_steps=["backup"],
            failures=[]
        )
        
        req = BackupRequest(backup_type="full")
        response = backup_project(project_id="proj_1", req=req, service=self.mock_service)
        
        self.assertEqual(response.status, "completed")

    def test_restore_project(self) -> None:
        self.mock_service.restore_project.return_value = OperationResponse(
            operation_id="op_3",
            status="completed",
            completed_steps=["restore"],
            failures=[]
        )
        
        req = RestoreRequest(backup_id="bak_123")
        response = restore_project(project_id="proj_1", req=req, service=self.mock_service)
        
        self.assertEqual(response.status, "completed")

    def test_health_check(self) -> None:
        self.mock_service.get_health.return_value = HealthResponse(
            project_id="proj_1",
            state="healthy",
            status="completed",
            success=True,
            message="OK"
        )
        
        response = get_health(project_id="proj_1", service=self.mock_service)
        
        self.assertTrue(response.success)
        self.assertEqual(response.state, "healthy")


if __name__ == "__main__":
    unittest.main()

