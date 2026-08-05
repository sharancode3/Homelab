from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


from app.platform.events.enums import EventCategory, EventPriority, EventStatus


@dataclass(frozen=True, slots=True)
class EventMetadata:
    version: str
    correlation_id: str
    source_component: str
    target_identity: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    event_id: str
    event_type: str
    category: EventCategory
    priority: EventPriority
    timestamp: datetime
    payload: dict[str, Any]
    metadata: EventMetadata
    status: EventStatus


@dataclass(frozen=True, slots=True)
class EventResult:
    event_id: str
    status: EventStatus
    delivered_to: tuple[str, ...]
    success: bool
    message: str
    error: str | None = None
