from typing import Any

from app.reliability.models import RecoveryRecord


class OperationRecoveryManager:
    """Manages tracking and recovery for failed operations."""

    def __init__(self) -> None:
        self._records: dict[str, RecoveryRecord] = {}

    def capture_failure(self, operation_id: str, project_id: str, operation_type: str, error_message: str, context_payload: dict[str, Any]) -> RecoveryRecord:
        """Capture a failed operation for later recovery analysis."""
        record = RecoveryRecord(
            operation_id=operation_id,
            project_id=project_id,
            operation_type=operation_type,
            error_message=error_message,
            context_payload=context_payload,
        )
        self._records[operation_id] = record
        return record

    def get_record(self, operation_id: str) -> RecoveryRecord | None:
        return self._records.get(operation_id)
