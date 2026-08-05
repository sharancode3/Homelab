class ReliabilityError(Exception):
    """Base exception for all reliability-related errors."""


class RetryExhaustedError(ReliabilityError):
    """Raised when an operation fails after exhausting all retry attempts."""


class NonRetryableError(ReliabilityError):
    """Raised when an operation fails with an error that should not be retried."""


class EventDeliveryError(ReliabilityError):
    """Raised when an event fails to be delivered to its target."""
