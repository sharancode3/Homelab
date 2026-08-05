import re
from typing import Any


class SecretsProtector:
    """Provides utilities to protect and mask sensitive information."""

    # Simple regex to detect common secret patterns in strings
    SECRET_PATTERNS = [
        re.compile(r"(?i)(password|passwd|pwd|secret|token|api_key|apikey|auth)[\s:=]+[\'\"]?([^\'\"\s,]+)[\'\"]?"),
        re.compile(r"(?i)bearer\s+([a-zA-Z0-9_\-\.]+)"),
    ]

    @classmethod
    def mask_string(cls, text: str) -> str:
        """Mask potential secrets in a string."""
        if not isinstance(text, str):
            return text
            
        masked = text
        for pattern in cls.SECRET_PATTERNS:
            def repl(m: re.Match) -> str:
                # If there are groups, mask the last group (the actual secret)
                if len(m.groups()) == 2:
                    full_match = m.group(0)
                    secret_val = m.group(2)
                    return full_match.replace(secret_val, "***MASKED***")
                elif len(m.groups()) == 1:
                    full_match = m.group(0)
                    secret_val = m.group(1)
                    return full_match.replace(secret_val, "***MASKED***")
                return "***MASKED***"
                
            masked = pattern.sub(repl, masked)
            
        return masked

    @classmethod
    def mask_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively mask secrets in a dictionary."""
        masked_data = {}
        for k, v in data.items():
            key_lower = k.lower()
            if any(term in key_lower for term in ["password", "secret", "token", "key"]):
                masked_data[k] = "***MASKED***"
            elif isinstance(v, dict):
                masked_data[k] = cls.mask_dict(v)
            elif isinstance(v, str):
                masked_data[k] = cls.mask_string(v)
            elif isinstance(v, list):
                masked_data[k] = [cls.mask_string(item) if isinstance(item, str) else item for item in v]
            else:
                masked_data[k] = v
        return masked_data
