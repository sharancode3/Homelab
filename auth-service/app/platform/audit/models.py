from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.platform.audit.enums import AuditCategory, AuditSeverity, AuditStatus


@dataclass(frozen=True, slots=True)
class AuditRecord:
    audit_id: str
    version: str
    timestamp: datetime
    category: AuditCategory
    event_type: str
    severity: AuditSeverity
    source_component: str
    target_identity: str | None
    correlation_id: str | None
    actor_context: dict[str, Any]
    outcome_status: AuditStatus
    summary: str
    details: dict[str, Any]
    integrity_marker: str
