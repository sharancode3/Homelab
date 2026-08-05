import unittest

from app.security.authorization import AuthorizationService
from app.security.exceptions import UnauthenticatedError, UnauthorizedError
from app.security.models import IdentityContext
from app.security.permissions import Permission, Role


class AuthorizationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.auth_service = AuthorizationService()

    def test_authorized_deploy(self) -> None:
        # Admin can deploy
        admin_identity = IdentityContext(user_id="u_admin", roles=frozenset([Role.ADMIN]))
        self.auth_service.check_permission(admin_identity, Permission.DEPLOY)
        
        # Operator can also deploy
        operator_identity = IdentityContext(user_id="u_op", roles=frozenset([Role.OPERATOR]))
        self.auth_service.check_permission(operator_identity, Permission.DEPLOY)

    def test_unauthorized_deploy(self) -> None:
        # Viewer cannot deploy
        viewer_identity = IdentityContext(user_id="u_viewer", roles=frozenset([Role.VIEWER]))
        with self.assertRaises(UnauthorizedError):
            self.auth_service.check_permission(viewer_identity, Permission.DEPLOY)

    def test_viewer_health_access(self) -> None:
        viewer_identity = IdentityContext(user_id="u_viewer", roles=frozenset([Role.VIEWER]))
        self.auth_service.check_permission(viewer_identity, Permission.HEALTH_VIEW)

    def test_missing_identity(self) -> None:
        with self.assertRaises(UnauthenticatedError):
            self.auth_service.check_permission(None, Permission.HEALTH_VIEW)

    def test_role_permission_mapping(self) -> None:
        admin_identity = IdentityContext(user_id="u_admin", roles=frozenset([Role.ADMIN]))
        
        # Admin should have all permissions
        for perm in Permission:
            self.auth_service.check_permission(admin_identity, perm)
            
        operator_identity = IdentityContext(user_id="u_op", roles=frozenset([Role.OPERATOR]))
        
        # Operator shouldn't have archive
        with self.assertRaises(UnauthorizedError):
            self.auth_service.check_permission(operator_identity, Permission.ARCHIVE)


if __name__ == "__main__":
    unittest.main()
