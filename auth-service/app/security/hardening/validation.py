import json
from typing import Any
import sys

from app.security.hardening.exceptions import InputSecurityError


class InputValidator:
    """Validates and sanitizes input data."""

    MAX_PAYLOAD_SIZE_BYTES = 1024 * 1024  # 1 MB
    DANGEROUS_TOKENS = ["<script>", "javascript:", "onload=", "onerror="]

    @classmethod
    def validate_payload(cls, payload: dict[str, Any]) -> None:
        """Validates that a payload is within size limits and contains no obvious dangerous input."""
        if not payload:
            return
            
        try:
            # Simple size check via JSON encoding
            serialized = json.dumps(payload)
            if sys.getsizeof(serialized) > cls.MAX_PAYLOAD_SIZE_BYTES:
                raise InputSecurityError("Payload exceeds maximum allowed size.")
        except TypeError:
            raise InputSecurityError("Payload is not JSON serializable.")
            
        # Recursive sanitization check
        cls._check_dangerous_content(payload)

    @classmethod
    def _check_dangerous_content(cls, data: Any) -> None:
        if isinstance(data, str):
            lower_data = data.lower()
            for token in cls.DANGEROUS_TOKENS:
                if token in lower_data:
                    raise InputSecurityError(f"Dangerous input detected: {token}")
        elif isinstance(data, dict):
            for v in data.values():
                cls._check_dangerous_content(v)
        elif isinstance(data, list):
            for item in data:
                cls._check_dangerous_content(item)
