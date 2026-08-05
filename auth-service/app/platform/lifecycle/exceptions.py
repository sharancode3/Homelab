from typing import final


@final
class ProjectNotFoundError(ValueError):
    """Raised when a project does not exist in the registry."""


@final
class InvalidTransitionError(ValueError):
    """Raised when a lifecycle transition is not allowed."""


@final
class LifecycleConflictError(ValueError):
    """Raised when a lifecycle operation conflicts with the current state."""
