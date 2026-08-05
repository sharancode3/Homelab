from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import secrets


@dataclass(slots=True, frozen=True)
class RetryConfig:
    max_attempts: int = 3
    initial_backoff_sec: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_sec: float = 30.0


@dataclass(slots=True, frozen=True)
class RecoveryRecord:
    operation_id: str
    project_id: str
    operation_type: str
    failed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: str = ""
    context_payload: dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    resolved: bool = False


@dataclass(slots=True, frozen=True)
class DeadLetterEvent:
    event_id: str = field(default_factory=lambda: secrets.token_hex(16))
    original_event_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    failed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
