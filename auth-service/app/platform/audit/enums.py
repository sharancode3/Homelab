from enum import Enum


class AuditCategory(str, Enum):
    SECURITY = "security"
    ACCESS = "access"
    LIFECYCLE = "lifecycle"
    CONFIGURATION = "configuration"
    SYSTEM = "system"


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
