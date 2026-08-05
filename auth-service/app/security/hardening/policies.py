from app.security.hardening.exceptions import PolicyViolationError
from app.security.models import IdentityContext, Permission


class SecurityPolicyEnforcer:
    """Enforces high-level security policies on operations."""

    @classmethod
    def check_operation_policy(cls, identity: IdentityContext, operation_type: str, project_id: str) -> None:
        """
        Validates if the identity is permitted to perform the operation on the project.
        This provides an extra boundary check above simple permission mapping.
        """
        # Example policy: only system or specific roles can do certain things
        if operation_type.lower() == "delete" and not cls._has_admin_rights(identity):
            raise PolicyViolationError("Only administrators can perform delete operations.")

    @classmethod
    def _has_admin_rights(cls, identity: IdentityContext) -> bool:
        # Simplistic check for policy boundary
        return any(role in ["admin", "system_admin"] for role in identity.roles)
