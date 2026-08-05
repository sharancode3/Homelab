from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import secrets


class LogSeverity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(slots=True, frozen=True)
class TraceContext:
    trace_id: str = field(default_factory=lambda: secrets.token_hex(16))
    correlation_id: str = field(default_factory=lambda: secrets.token_hex(16))

    def propagate(self, new_correlation_id: str | None = None) -> "TraceContext":
        """Propagate trace context, generating a new correlation ID if needed."""
        return TraceContext(
            trace_id=self.trace_id,
            correlation_id=new_correlation_id or secrets.token_hex(16),
        )


@dataclass(slots=True, frozen=True)
class LogEntry:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    severity: LogSeverity = LogSeverity.INFO
    operation_id: str | None = None
    correlation_id: str | None = None
    project_id: str | None = None
    component: str = "system"
    event_type: str = "event"
    message: str = ""
