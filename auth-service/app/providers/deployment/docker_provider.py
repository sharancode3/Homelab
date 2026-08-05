import secrets
import subprocess
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
    It uses a safe simulated interaction layer when `simulate=True`.
    In real mode (`simulate=False`), it uses the docker CLI via subprocess.
    """

    def __init__(self, simulate: bool = True) -> None:
        self.simulate = simulate
        # Simulated state: mapping deployment handles to their configuration and status
        self._deployments: dict[str, dict[str, Any]] = {}

    def _get_container_name(self, project_id: str, handle: str) -> str:
        return f"platform-{project_id}-{handle.split('_')[-1]}"

    def prepare_deployment(self, project_id: str, configuration: dict[str, Any]) -> str:
        """Prepare deployment and return a deployment handle."""
        if not project_id:
            raise DockerPreparationError("Project ID is required.")
        
        if "image" not in configuration:
            raise DockerPreparationError("Configuration must specify 'image'.")
        
        if not self.simulate:
            # Check Docker availability
            try:
                subprocess.run(
                    ["docker", "info"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                raise DockerPreparationError("Docker is not available or not running.") from e

        deployment_handle = f"deploy_{project_id}_{secrets.token_hex(4)}"
        
        self._deployments[deployment_handle] = {
            "project_id": project_id,
            "configuration": configuration,
            "status": "prepared",
            "container_name": self._get_container_name(project_id, deployment_handle),
        }
        
        return deployment_handle

    def execute_deployment(self, deployment_handle: str) -> bool:
        """Execute the prepared deployment action."""
        if deployment_handle not in self._deployments:
            raise DockerExecutionError(f"Unknown deployment handle: {deployment_handle}")
        
        deployment = self._deployments[deployment_handle]
        if deployment["status"] != "prepared":
            raise DockerExecutionError(f"Deployment {deployment_handle} is not in 'prepared' state.")
        
        if self.simulate:
            deployment["status"] = "running"
            return True
            
        # Real execution path
        config = deployment["configuration"]
        container_name = deployment["container_name"]
        
        cmd = ["docker", "run", "-d", "--name", container_name]
        
        # Map ports if present (e.g., ["8000:8000"])
        ports = config.get("ports", [])
        for port_mapping in ports:
            cmd.extend(["-p", port_mapping])
            
        # Add environment variables
        env_vars = config.get("environment", {})
        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])
            
        cmd.append(config["image"])
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            deployment["status"] = "running"
            return True
        except subprocess.CalledProcessError as e:
            deployment["status"] = "failed"
            raise DockerExecutionError(f"Docker run failed: {e.stderr}") from e
        except FileNotFoundError as e:
            deployment["status"] = "failed"
            raise DockerExecutionError("Docker command not found.") from e

    def check_status(self, deployment_handle: str) -> str:
        """Check the current status of a deployment."""
        if deployment_handle not in self._deployments:
            return "unknown"
            
        deployment = self._deployments[deployment_handle]
        
        if self.simulate or deployment["status"] in ["prepared", "rolled_back", "unknown"]:
            return deployment["status"]
            
        # Real status check
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", deployment["container_name"]],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            # Docker status outputs can be 'running', 'exited', 'dead', etc.
            status = result.stdout.strip()
            if status == "running":
                deployment["status"] = "running"
            else:
                deployment["status"] = f"stopped ({status})"
            return deployment["status"]
        except subprocess.CalledProcessError:
            return "unknown"

    def rollback(self, deployment_handle: str) -> bool:
        """Rollback a failed or active deployment."""
        if deployment_handle not in self._deployments:
            raise DockerRollbackError(f"Unknown deployment handle: {deployment_handle}")
            
        deployment = self._deployments[deployment_handle]
        
        if self.simulate:
            deployment["status"] = "rolled_back"
            return True
            
        container_name = deployment["container_name"]
        try:
            subprocess.run(
                ["docker", "stop", container_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["docker", "rm", container_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            deployment["status"] = "rolled_back"
            return True
        except FileNotFoundError as e:
            raise DockerRollbackError("Docker command not found.") from e
