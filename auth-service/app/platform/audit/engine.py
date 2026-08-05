import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from app.platform.audit.enums import AuditCategory, AuditSeverity, AuditStatus
from app.platform.audit.exceptions import AuditIntegrityError, AuditRecordError
from app.platform.audit.models import AuditRecord


class AuditEngine:
    """Append-only, immutable recording layer for platform audit events."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def record_event(
        self,
        category: AuditCategory,
        event_type: str,
        severity: AuditSeverity,
        source_component: str,
        outcome_status: AuditStatus,
        summary: str,
        target_identity: str | None = None,
        correlation_id: str | None = None,
        actor_context: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        version: str = "1.0",
    ) -> AuditRecord:
        """Create and append a new immutable audit record."""
        
        self._validate_input(event_type, source_component, summary)
        
        timestamp = datetime.now(timezone.utc)
        audit_id = f"aud_{os.urandom(8).hex()}"
        actor_ctx = actor_context or {}
        dtls = details or {}
        
        marker = self._generate_integrity_marker(
            audit_id, version, timestamp, category, event_type, severity,
            source_component, target_identity, correlation_id, actor_ctx,
            outcome_status, summary, dtls
        )

        record = AuditRecord(
            audit_id=audit_id,
            version=version,
            timestamp=timestamp,
            category=category,
            event_type=event_type,
            severity=severity,
            source_component=source_component,
            target_identity=target_identity,
            correlation_id=correlation_id,
            actor_context=actor_ctx,
            outcome_status=outcome_status,
            summary=summary,
            details=dtls,
            integrity_marker=marker,
        )

        self._records.append(record)
        return record

    def verify_integrity(self, record: AuditRecord) -> bool:
        """Verify that a record has not been tampered with."""
        expected_marker = self._generate_integrity_marker(
            record.audit_id, record.version, record.timestamp, record.category,
            record.event_type, record.severity, record.source_component,
            record.target_identity, record.correlation_id, record.actor_context,
            record.outcome_status, record.summary, record.details
        )
        return record.integrity_marker == expected_marker

    def query(
        self,
        project_id: str | None = None,
        category: AuditCategory | None = None,
        correlation_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[AuditRecord]:
        """Query the audit history with filtering."""
        results = []
        for record in self._records:
            if project_id and record.target_identity != project_id:
                continue
            if category and record.category is not category:
                continue
            if correlation_id and record.correlation_id != correlation_id:
                continue
            if start_time and record.timestamp < start_time:
                continue
            if end_time and record.timestamp > end_time:
                continue
            results.append(record)
        return results

    def _validate_input(self, event_type: str, source_component: str, summary: str) -> None:
        if not event_type.strip():
            raise AuditRecordError("Event type is required.")
        if not source_component.strip():
            raise AuditRecordError("Source component is required.")
        if not summary.strip():
            raise AuditRecordError("Summary is required.")

    def _generate_integrity_marker(
        self,
        audit_id: str,
        version: str,
        timestamp: datetime,
        category: AuditCategory,
        event_type: str,
        severity: AuditSeverity,
        source_component: str,
        target_identity: str | None,
        correlation_id: str | None,
        actor_context: dict[str, Any],
        outcome_status: AuditStatus,
        summary: str,
        details: dict[str, Any],
    ) -> str:
        payload = {
            "audit_id": audit_id,
            "version": version,
            "timestamp": timestamp.isoformat(),
            "category": category.value,
            "event_type": event_type,
            "severity": severity.value,
            "source_component": source_component,
            "target_identity": target_identity,
            "correlation_id": correlation_id,
            "actor_context": actor_context,
            "outcome_status": outcome_status.value,
            "summary": summary,
            "details": details,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
