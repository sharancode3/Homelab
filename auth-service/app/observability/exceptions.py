class ObservabilityError(Exception):
    """Base exception for all observability-related errors."""


class MetricError(ObservabilityError):
    """Raised when an error occurs in metrics recording."""


class TraceError(ObservabilityError):
    """Raised when an error occurs in trace propagation."""
