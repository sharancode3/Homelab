from enum import Enum


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthStatus(str, Enum):
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


class HealthSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class HealthCategory(str, Enum):
    DATABASE = "database"
    API = "api"
    WORKER = "worker"
    SYSTEM = "system"
    INFRASTRUCTURE = "infrastructure"
