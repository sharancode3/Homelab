import subprocess
import unittest
from unittest.mock import MagicMock, patch

from app.providers.deployment.docker_provider import DockerDeploymentProvider
from app.providers.deployment.exceptions import (
    DockerExecutionError,
    DockerPreparationError,
    DockerRollbackError,
)


class DockerDeploymentProviderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = DockerDeploymentProvider(simulate=True)
        self.project_id = "proj_test_123"
        self.valid_config = {"image": "my-app:latest", "port": 8080}

    def test_deployment_preparation_success(self) -> None:
        handle = self.provider.prepare_deployment(self.project_id, self.valid_config)
        self.assertTrue(handle.startswith(f"deploy_{self.project_id}_"))
        self.assertEqual(self.provider.check_status(handle), "prepared")

    def test_deployment_preparation_failure(self) -> None:
        # Missing project ID
        with self.assertRaises(DockerPreparationError):
            self.provider.prepare_deployment("", self.valid_config)
            
        # Missing required configuration (e.g., 'image')
        with self.assertRaises(DockerPreparationError):
            self.provider.prepare_deployment(self.project_id, {"port": 8080})

    def test_successful_execution(self) -> None:
        handle = self.provider.prepare_deployment(self.project_id, self.valid_config)
        self.assertEqual(self.provider.check_status(handle), "prepared")
        
        result = self.provider.execute_deployment(handle)
        self.assertTrue(result)
        self.assertEqual(self.provider.check_status(handle), "running")

    def test_execution_failure_handling(self) -> None:
        # Unknown handle
        with self.assertRaises(DockerExecutionError):
            self.provider.execute_deployment("unknown_handle")
            
        handle = self.provider.prepare_deployment(self.project_id, self.valid_config)
        
        # Execute it once successfully
        self.provider.execute_deployment(handle)
        
        # Trying to execute it again when it is 'running' instead of 'prepared'
        with self.assertRaises(DockerExecutionError):
            self.provider.execute_deployment(handle)

    def test_status_checking(self) -> None:
        self.assertEqual(self.provider.check_status("unknown_handle"), "unknown")
        
        handle = self.provider.prepare_deployment(self.project_id, self.valid_config)
        self.assertEqual(self.provider.check_status(handle), "prepared")
        
        self.provider.execute_deployment(handle)
        self.assertEqual(self.provider.check_status(handle), "running")

    def test_rollback_behavior(self) -> None:
        # Unknown handle
        with self.assertRaises(DockerRollbackError):
            self.provider.rollback("unknown_handle")
            
        handle = self.provider.prepare_deployment(self.project_id, self.valid_config)
        self.provider.execute_deployment(handle)
        
        result = self.provider.rollback(handle)
        self.assertTrue(result)
        self.assertEqual(self.provider.check_status(handle), "rolled_back")

    @patch("app.providers.deployment.docker_provider.subprocess.run")
    def test_real_preparation_success(self, mock_run) -> None:
        real_provider = DockerDeploymentProvider(simulate=False)
        mock_run.return_value = MagicMock(returncode=0)
        handle = real_provider.prepare_deployment(self.project_id, self.valid_config)
        self.assertTrue(handle.startswith(f"deploy_{self.project_id}_"))
        mock_run.assert_called_once_with(
            ["docker", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    @patch("app.providers.deployment.docker_provider.subprocess.run")
    def test_real_execution_success(self, mock_run) -> None:
        real_provider = DockerDeploymentProvider(simulate=False)
        mock_run.return_value = MagicMock(returncode=0)
        
        config_with_ports = {"image": "my-app:latest", "ports": ["8080:8000"], "environment": {"ENV": "prod"}}
        handle = real_provider.prepare_deployment(self.project_id, config_with_ports)
        
        mock_run.reset_mock()
        mock_run.return_value = MagicMock(returncode=0, stdout="running\n")
        result = real_provider.execute_deployment(handle)
        
        self.assertTrue(result)
        self.assertEqual(real_provider.check_status(handle), "running")
        
        container_name = real_provider._deployments[handle]["container_name"]
        mock_run.assert_any_call(
            ["docker", "run", "-d", "--name", container_name, "-p", "8080:8000", "-e", "ENV=prod", "my-app:latest"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

    @patch("app.providers.deployment.docker_provider.subprocess.run")
    def test_real_status_check(self, mock_run) -> None:
        real_provider = DockerDeploymentProvider(simulate=False)
        mock_run.return_value = MagicMock(returncode=0)
        handle = real_provider.prepare_deployment(self.project_id, self.valid_config)
        real_provider._deployments[handle]["status"] = "running"
        
        mock_run.reset_mock()
        mock_run.return_value = MagicMock(stdout="exited\n")
        
        status = real_provider.check_status(handle)
        self.assertEqual(status, "stopped (exited)")
        
        mock_run.return_value = MagicMock(stdout="running\n")
        status = real_provider.check_status(handle)
        self.assertEqual(status, "running")

    @patch("app.providers.deployment.docker_provider.subprocess.run")
    def test_real_rollback(self, mock_run) -> None:
        real_provider = DockerDeploymentProvider(simulate=False)
        mock_run.return_value = MagicMock(returncode=0)
        handle = real_provider.prepare_deployment(self.project_id, self.valid_config)
        real_provider.execute_deployment(handle)
        
        mock_run.reset_mock()
        result = real_provider.rollback(handle)
        
        self.assertTrue(result)
        self.assertEqual(real_provider.check_status(handle), "rolled_back")
        self.assertEqual(mock_run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
