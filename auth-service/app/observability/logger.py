import json
from dataclasses import asdict
from sys import stdout

from app.observability.models import LogEntry, LogSeverity
from app.security.hardening.secrets import SecretsProtector


class StructuredLogger:
    """Provides structured logging for the platform."""

    def __init__(self, component: str = "system") -> None:
        self.component = component
        self.sink = stdout

    def _log(
        self,
        severity: LogSeverity,
        event_type: str,
        message: str,
        operation_id: str | None = None,
        correlation_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        entry = LogEntry(
            severity=severity,
            component=self.component,
            event_type=event_type,
            message=message,
            operation_id=operation_id,
            correlation_id=correlation_id,
            project_id=project_id,
        )
        
        # In a real environment we would use a logging framework (like structlog or standard logging)
        # Here we just output JSON to stdout.
        entry_dict = asdict(entry)
        entry_dict["timestamp"] = entry_dict["timestamp"].isoformat()
        
        # Mask secrets before logging
        masked_dict = SecretsProtector.mask_dict(entry_dict)
        
        self.sink.write(json.dumps(masked_dict) + "\n")
        self.sink.flush()

    def info(self, event_type: str, message: str, **kwargs: str | None) -> None:
        self._log(LogSeverity.INFO, event_type, message, **kwargs)

    def error(self, event_type: str, message: str, **kwargs: str | None) -> None:
        self._log(LogSeverity.ERROR, event_type, message, **kwargs)

    def warn(self, event_type: str, message: str, **kwargs: str | None) -> None:
        self._log(LogSeverity.WARN, event_type, message, **kwargs)

    def debug(self, event_type: str, message: str, **kwargs: str | None) -> None:
        self._log(LogSeverity.DEBUG, event_type, message, **kwargs)
