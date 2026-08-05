class SecurityHardeningError(Exception):
    """Base exception for all security hardening errors."""


class InputSecurityError(SecurityHardeningError):
    """Raised when an input violates security boundaries (size, sanitization)."""


class AuditIntegrityError(SecurityHardeningError):
    """Raised when audit record integrity check fails."""


class PolicyViolationError(SecurityHardeningError):
    """Raised when an operation violates security policy."""
