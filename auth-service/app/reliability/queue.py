from typing import Any

from app.reliability.exceptions import EventDeliveryError
from app.reliability.models import DeadLetterEvent


class DeadLetterQueue:
    """Stores events that failed to be delivered."""

    def __init__(self) -> None:
        self._dead_letters: list[DeadLetterEvent] = []

    def store_failed_event(self, event_type: str, payload: dict[str, Any], reason: str) -> str:
        """Store an event that failed to deliver in the dead-letter queue."""
        event = DeadLetterEvent(
            original_event_type=event_type,
            payload=payload,
            reason=reason,
        )
        self._dead_letters.append(event)
        return event.event_id

    def get_events(self) -> list[DeadLetterEvent]:
        return list(self._dead_letters)


class EventReliabilityManager:
    """Wraps event delivery with reliability mechanics."""
    
    def __init__(self, dlq: DeadLetterQueue) -> None:
        self.dlq = dlq
        
    def handle_delivery_failure(self, event_type: str, payload: dict[str, Any], error: Exception) -> str:
        """Handle a failure in event delivery by routing to DLQ."""
        return self.dlq.store_failed_event(event_type, payload, str(error))
