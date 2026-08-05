from app.security.exceptions import UnauthenticatedError, UnauthorizedError
from app.security.models import IdentityContext
from app.security.permissions import Permission
from app.security.hardening.policies import SecurityPolicyEnforcer


class AuthorizationService:
    """Handles authorization checks against identity contexts."""

    def check_permission(self, identity: IdentityContext | None, permission: Permission) -> None:
        """
        Verify that the given identity has the required permission.
        Raises UnauthenticatedError if no identity is provided.
        Raises UnauthorizedError if the identity lacks the permission.
        """
        if not identity:
            raise UnauthenticatedError("No identity provided for authorized operation.")
            
        if permission not in identity.permissions:
            raise UnauthorizedError(
                f"Identity {identity.user_id} lacks required permission: {permission.value}"
            )

    def check_policy(self, identity: IdentityContext | None, operation_type: str, project_id: str) -> None:
        """
        Verify that the given identity satisfies the high-level security policy for the operation.
        Raises UnauthenticatedError if no identity is provided.
        Raises PolicyViolationError if the policy is violated.
        """
        if not identity:
            raise UnauthenticatedError("No identity provided for policy check.")
            
        SecurityPolicyEnforcer.check_operation_policy(identity, operation_type, project_id)
