class AuditException(Exception):
    """Base exception for all audit engine errors."""


class AuditRecordError(AuditException):
    """Raised when an audit record is invalid or cannot be created."""


class AuditIntegrityError(AuditException):
    """Raised when an audit record's integrity verification fails."""
