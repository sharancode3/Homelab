import unittest

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

    def test_real_execution_raises_error(self) -> None:
        real_provider = DockerDeploymentProvider(simulate=False)
        handle = real_provider.prepare_deployment(self.project_id, self.valid_config)
        
        with self.assertRaises(DockerExecutionError):
            real_provider.execute_deployment(handle)
            
        with self.assertRaises(DockerRollbackError):
            real_provider.rollback(handle)


if __name__ == "__main__":
    unittest.main()
