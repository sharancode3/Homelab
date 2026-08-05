import hashlib
import json
from typing import Any

from app.security.hardening.exceptions import AuditIntegrityError


class AuditSecurityLayer:
    """Provides security functions for the audit engine boundary."""

    @staticmethod
    def generate_record_hash(payload: dict[str, Any]) -> str:
        """Generates a cryptographic hash for an audit record."""
        # Serialize deterministically
        serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    @classmethod
    def verify_record_integrity(cls, payload: dict[str, Any], record_hash: str) -> None:
        """Verifies that an audit record has not been tampered with."""
        expected_hash = cls.generate_record_hash(payload)
        if expected_hash != record_hash:
            raise AuditIntegrityError(f"Audit record integrity check failed.")
