import secrets
from typing import Any

from app.adapters.interfaces import DeploymentAdapter
from app.providers.deployment.exceptions import (
    DockerExecutionError,
    DockerPreparationError,
    DockerRollbackError,
)


class DockerDeploymentProvider(DeploymentAdapter):
    """
    A Docker-based implementation of the DeploymentAdapter contract.
    For this phase, it uses a safe simulated interaction layer to avoid
    requiring a real Docker daemon during testing and initial deployment.
    """

    def __init__(self, simulate: bool = True) -> None:
        self.simulate = simulate
        # Simulated state: mapping deployment handles to their configuration and status
        self._deployments: dict[str, dict[str, Any]] = {}

    def prepare_deployment(self, project_id: str, configuration: dict[str, Any]) -> str:
        """Prepare deployment and return a deployment handle."""
        if not project_id:
            raise DockerPreparationError("Project ID is required.")
        
        # In a real provider, we might template a docker-compose.yml or parse image tags.
        # Here we simulate preparation.
        deployment_handle = f"deploy_{project_id}_{secrets.token_hex(4)}"
        
        # Ensure image is provided as an example of validation
        if "image" not in configuration:
            raise DockerPreparationError("Configuration must specify 'image'.")
        
        self._deployments[deployment_handle] = {
            "project_id": project_id,
            "configuration": configuration,
            "status": "prepared",
        }
        
        return deployment_handle

    def execute_deployment(self, deployment_handle: str) -> bool:
        """Execute the prepared deployment action."""
        if deployment_handle not in self._deployments:
            raise DockerExecutionError(f"Unknown deployment handle: {deployment_handle}")
        
        deployment = self._deployments[deployment_handle]
        if deployment["status"] != "prepared":
            raise DockerExecutionError(f"Deployment {deployment_handle} is not in 'prepared' state.")
        
        # Simulate execution
        # In a real provider, we would call docker CLI or API here
        if self.simulate:
            deployment["status"] = "running"
            return True
            
        # Real execution path not yet required/implemented
        raise DockerExecutionError("Real execution is not yet implemented.")

    def check_status(self, deployment_handle: str) -> str:
        """Check the current status of a deployment."""
        if deployment_handle not in self._deployments:
            return "unknown"
            
        return self._deployments[deployment_handle]["status"]

    def rollback(self, deployment_handle: str) -> bool:
        """Rollback a failed or active deployment."""
        if deployment_handle not in self._deployments:
            raise DockerRollbackError(f"Unknown deployment handle: {deployment_handle}")
            
        deployment = self._deployments[deployment_handle]
        
        # Simulate rollback
        if self.simulate:
            deployment["status"] = "rolled_back"
            return True
            
        raise DockerRollbackError("Real rollback is not yet implemented.")
