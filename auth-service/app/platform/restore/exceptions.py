class RestoreException(Exception):
    """Base exception for all restore engine errors."""


class RestoreRequestError(RestoreException):
    """Raised when a restore request is invalid."""


class RestoreManifestError(RestoreException):
    """Raised when a backup manifest is invalid or unreadable."""


class RestorePlanError(RestoreException):
    """Raised when a restore plan is invalid or cannot be created."""


class RestoreCompatibilityError(RestoreException):
    """Raised when the backup is not compatible with the current environment."""


class RestoreVerificationError(RestoreException):
    """Raised when restore verification fails."""


class RestoreExecutionError(RestoreException):
    """Raised when a restore execution fails."""
