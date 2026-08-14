import unittest
from unittest.mock import MagicMock
from app.api.baas_service import BaaSProjectServiceLayer
from app.api.service import APIServiceLayer
from app.project_registry_manager import ProjectRegistryManager
from app.api.models import StopRequest, RestartRequest, LogsResponse, LogEventResponse, OperationResponse
from datetime import datetime, timezone

class TestBaaSDeploymentIntegration(unittest.TestCase):
    def setUp(self):
        self.registry = MagicMock(spec=ProjectRegistryManager)
        self.internal_service = MagicMock(spec=APIServiceLayer)
        self.authz_repo = MagicMock()
        self.user_repo = MagicMock()
        
        self.service = BaaSProjectServiceLayer(
            self.internal_service, self.authz_repo, self.registry, self.user_repo
        )
        self.project_id = "proj_test_deploy"

    def test_stop_project_success(self):
        req = StopRequest(requested_by="u1", correlation_id="c1")
        mock_resp = OperationResponse(
            operation_id="op_123", status="completed", completed_steps=["stop"], failures=[]
        )
        self.internal_service.stop_project.return_value = mock_resp
        
        resp = self.service.stop_project(self.project_id, req)
        
        self.internal_service.stop_project.assert_called_once_with(self.project_id, req)
        self.assertEqual(resp.operation_id, "op_123")
        self.assertEqual(resp.status, "completed")
        self.assertIn("stop", resp.completed_steps)

    def test_restart_project_success(self):
        req = RestartRequest(requested_by="u1", correlation_id="c2")
        mock_resp = OperationResponse(
            operation_id="op_456", status="completed", completed_steps=["stop", "start"], failures=[]
        )
        self.internal_service.restart_project.return_value = mock_resp
        
        resp = self.service.restart_project(self.project_id, req)
        
        self.internal_service.restart_project.assert_called_once_with(self.project_id, req)
        self.assertEqual(resp.operation_id, "op_456")
        self.assertEqual(resp.status, "completed")
        self.assertIn("start", resp.completed_steps)

    def test_get_logs_success(self):
        mock_logs = LogsResponse(
            project_id=self.project_id,
            logs=[
                LogEventResponse(
                    audit_id="a1",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event_type="deploy_started",
                    severity="info",
                    message="Deployment started"
                )
            ]
        )
        self.internal_service.get_project_logs.return_value = mock_logs
        
        resp = self.service.get_project_logs(self.project_id, 100)
        
        self.internal_service.get_project_logs.assert_called_once_with(self.project_id, 100)
        self.assertEqual(len(resp.logs), 1)
        self.assertEqual(resp.logs[0].event_type, "deploy_started")

if __name__ == "__main__":
    unittest.main()
