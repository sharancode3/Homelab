from typing import final


@final
class ValidationException(Exception):
    """Base class for validation errors."""


@final
class ValidationRequestException(ValidationException):
    """Raised when the validation request itself is invalid."""


@final
class ProjectValidationException(ValidationException):
    """Raised when project validation fails."""


@final
class LifecycleValidationException(ValidationException):
    """Raised when lifecycle validation fails."""


@final
class ConfigurationValidationException(ValidationException):
    """Raised when configuration validation fails."""


@final
class OperationValidationException(ValidationException):
    """Raised when operation validation fails."""
