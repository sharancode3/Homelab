class SecurityError(Exception):
    """Base exception for all security-related errors."""


class UnauthorizedError(SecurityError):
    """Raised when an identity is not authorized to perform an action."""


class UnauthenticatedError(SecurityError):
    """Raised when an identity context is missing or invalid."""
