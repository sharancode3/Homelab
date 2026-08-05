class HealthException(Exception):
    """Base exception for all health engine errors."""


class HealthRequestError(HealthException):
    """Raised when a health check request is invalid."""


class HealthEvaluationError(HealthException):
    """Raised when the health evaluation process fails."""
