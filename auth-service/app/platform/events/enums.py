from enum import Enum


class EventCategory(str, Enum):
    SYSTEM = "system"
    LIFECYCLE = "lifecycle"
    AUDIT = "audit"
    SECURITY = "security"
    DATA = "data"


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(str, Enum):
    CREATED = "created"
    PUBLISHED = "published"
    ROUTED = "routed"
    RECORDED = "recorded"
    DELIVERED = "delivered"
    FAILED = "failed"


class DeliveryGuarantee(str, Enum):
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"
