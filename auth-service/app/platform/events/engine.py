from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from app.platform.events.enums import DeliveryGuarantee, EventCategory, EventPriority, EventStatus
from app.platform.events.exceptions import EventException, EventValidationError, EventDeliveryError
from app.platform.events.models import EventEnvelope, EventMetadata, EventResult


class EventEngine:
    """Publish, route, and record layer for immutable events."""

    def __init__(self) -> None:
        # Mock storage for recorded events
        self._recorded_events: dict[str, EventEnvelope] = {}
        # Mock route configurations
        self._routes: dict[str, list[str]] = {}
        # Default guarantee
        self._default_guarantee = DeliveryGuarantee.AT_LEAST_ONCE

    def register_route(self, category: EventCategory, target: str) -> None:
        """Register a destination target for an event category."""
        if category.value not in self._routes:
            self._routes[category.value] = []
        if target not in self._routes[category.value]:
            self._routes[category.value].append(target)

    def publish(
        self,
        event_type: str,
        category: EventCategory,
        priority: EventPriority,
        payload: dict[str, Any],
        correlation_id: str,
        source_component: str,
        version: str = "1.0",
        target_identity: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> EventResult:
        """Create, route, record and deliver an event."""
        
        event_id = f"evt_{os.urandom(8).hex()}"
        
        try:
            # 1. Validation
            self._validate_input(event_type, correlation_id, version, source_component)
            
            # 2. Creation
            metadata = EventMetadata(
                version=version,
                correlation_id=correlation_id,
                source_component=source_component,
                target_identity=target_identity,
                extra=extra_metadata or {},
            )
            
            event = EventEnvelope(
                event_id=event_id,
                event_type=event_type,
                category=category,
                priority=priority,
                timestamp=datetime.now(timezone.utc),
                payload=payload,
                metadata=metadata,
                status=EventStatus.CREATED,
            )
            
            # 3. Publish
            event = replace(event, status=EventStatus.PUBLISHED)
            
            # 4. Route
            targets = self._resolve_routes(event)
            event = replace(event, status=EventStatus.ROUTED)
            
            # 5. Record
            self._record_event(event)
            event = replace(event, status=EventStatus.RECORDED)
            
            # 6. Deliver
            delivered_to = self._deliver_event(event, targets)
            event = replace(event, status=EventStatus.DELIVERED)
            
            # Update record with final status
            self._record_event(event)
            
            return EventResult(
                event_id=event.event_id,
                status=event.status,
                delivered_to=tuple(delivered_to),
                success=True,
                message="Event published and delivered successfully.",
            )
            
        except EventException as error:
            return EventResult(
                event_id=event_id,
                status=EventStatus.FAILED,
                delivered_to=(),
                success=False,
                message=str(error),
                error=str(error),
            )
        except Exception as error:
            return EventResult(
                event_id=event_id,
                status=EventStatus.FAILED,
                delivered_to=(),
                success=False,
                message=f"Unexpected error: {str(error)}",
                error=str(error),
            )

    def _validate_input(
        self, event_type: str, correlation_id: str, version: str, source_component: str
    ) -> None:
        if not event_type.strip():
            raise EventValidationError("Event type is required.")
        if not correlation_id.strip():
            raise EventValidationError("Correlation ID is required.")
        if not version.strip():
            raise EventValidationError("Version is required.")
        if not source_component.strip():
            raise EventValidationError("Source component is required.")

    def _resolve_routes(self, event: EventEnvelope) -> list[str]:
        """Deterministic rule-based routing."""
        targets = list(self._routes.get(event.category.value, []))
        if event.metadata.target_identity and event.metadata.target_identity not in targets:
            targets.append(event.metadata.target_identity)
            
        return targets

    def _record_event(self, event: EventEnvelope) -> None:
        """Simulate immutable event recording."""
        self._recorded_events[event.event_id] = event

    def _deliver_event(self, event: EventEnvelope, targets: list[str]) -> list[str]:
        """Simulate delivery to targets."""
        # For simulation, assume all targets accept the event successfully
        if not targets and event.category is not EventCategory.SYSTEM:
            # Maybe just warn, but we can return empty
            pass
        return targets
