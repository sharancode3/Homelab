from typing import final


@final
class DeploymentException(Exception):
    """Base class for deployment errors."""


@final
class DeploymentRequestError(DeploymentException):
    """Raised when the deployment request is invalid."""


@final
class DeploymentPlanError(DeploymentException):
    """Raised when the deployment plan cannot be produced."""


@final
class DeploymentVerificationError(DeploymentException):
    """Raised when deployment verification fails."""
