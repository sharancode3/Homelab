from app.adapters.exceptions import DeploymentAdapterError


class DockerProviderError(DeploymentAdapterError):
    """Base exception for Docker deployment provider errors."""


class DockerPreparationError(DockerProviderError):
    """Raised when preparing a Docker deployment fails."""


class DockerExecutionError(DockerProviderError):
    """Raised when executing a Docker deployment fails."""


class DockerRollbackError(DockerProviderError):
    """Raised when rolling back a Docker deployment fails."""
