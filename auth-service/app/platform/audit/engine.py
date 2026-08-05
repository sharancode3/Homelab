import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from app.platform.audit.enums import AuditCategory, AuditSeverity, AuditStatus
from app.platform.audit.exceptions import AuditIntegrityError, AuditRecordError
from app.platform.audit.models import AuditRecord
from app.security.hardening.audit_security import AuditSecurityLayer
from app.security.hardening.exceptions import AuditIntegrityError
from app.storage.interfaces import AuditRepository


class AuditEngine:
    """Append-only, immutable recording layer for platform audit events."""

    def __init__(self, repository: AuditRepository) -> None:
        self._repository = repository

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

        self._repository.append(record)
        return record

    def verify_integrity(self, record: AuditRecord) -> bool:
        """Verify that a record has not been tampered with."""
        payload = {
            "audit_id": record.audit_id,
            "version": record.version,
            "timestamp": record.timestamp.isoformat(),
            "category": record.category.value,
            "event_type": record.event_type,
            "severity": record.severity.value,
            "source_component": record.source_component,
            "target_identity": record.target_identity,
            "correlation_id": record.correlation_id,
            "actor_context": record.actor_context,
            "outcome_status": record.outcome_status.value,
            "summary": record.summary,
            "details": record.details,
        }
        try:
            AuditSecurityLayer.verify_record_integrity(payload, record.integrity_marker)
            return True
        except AuditIntegrityError:
            return False

    def query(
        self,
        project_id: str | None = None,
        category: AuditCategory | None = None,
        correlation_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[AuditRecord]:
        """Query the audit history with filtering."""
        return self._repository.query(
            project_id=project_id,
            category=category,
            correlation_id=correlation_id,
            start_time=start_time,
            end_time=end_time,
        )

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
        return AuditSecurityLayer.generate_record_hash(payload)
