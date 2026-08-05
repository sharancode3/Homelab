class EventException(Exception):
    """Base exception for all event engine errors."""


class EventCreationError(EventException):
    """Raised when an event cannot be created."""


class EventRoutingError(EventException):
    """Raised when an event cannot be routed."""


class EventDeliveryError(EventException):
    """Raised when an event cannot be delivered."""


class EventValidationError(EventException):
    """Raised when an event is invalid."""
