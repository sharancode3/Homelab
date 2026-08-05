class OperationException(Exception):
    """Base exception for all operation engine errors."""


class OperationRequestError(OperationException):
    """Raised when an operation request is invalid."""


class OperationConflictError(OperationException):
    """Raised when an operation conflicts with an already running operation."""


class OperationExecutionError(OperationException):
    """Raised when an operation execution fails."""
