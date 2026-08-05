import unittest

from app.security.hardening.audit_security import AuditSecurityLayer
from app.security.hardening.exceptions import (
    AuditIntegrityError,
    InputSecurityError,
    PolicyViolationError,
)
from app.security.hardening.policies import SecurityPolicyEnforcer
from app.security.hardening.secrets import SecretsProtector
from app.security.hardening.validation import InputValidator
from app.security.models import IdentityContext, Permission


class SecurityHardeningTestCase(unittest.TestCase):
    def test_secret_masking(self) -> None:
        log_payload = {
            "user": "test_user",
            "password": "supersecretpassword",
            "token": "api_key_12345",
            "metadata": {
                "apiKey": "abcde"
            }
        }
        masked = SecretsProtector.mask_dict(log_payload)
        
        self.assertEqual(masked["user"], "test_user")
        self.assertEqual(masked["password"], "***MASKED***")
        self.assertEqual(masked["token"], "***MASKED***")
        self.assertEqual(masked["metadata"]["apiKey"], "***MASKED***")
        
        text = "Connecting with DB_PASSWORD='my_db_password'"
        masked_text = SecretsProtector.mask_string(text)
        self.assertNotIn("my_db_password", masked_text)
        self.assertIn("***MASKED***", masked_text)

    def test_invalid_input_rejection(self) -> None:
        valid_payload = {"project_id": "proj_1", "action": "deploy"}
        InputValidator.validate_payload(valid_payload)  # Should not raise
        
        invalid_payload = {"description": "deploy <script>alert(1)</script>"}
        with self.assertRaises(InputSecurityError):
            InputValidator.validate_payload(invalid_payload)

    def test_audit_integrity(self) -> None:
        payload = {
            "action": "deploy",
            "resource": "proj_1",
            "timestamp": "2026-08-05T00:00:00Z",
            "details": {"status": "success"},
        }
        
        valid_hash = AuditSecurityLayer.generate_record_hash(payload)
        AuditSecurityLayer.verify_record_integrity(payload, valid_hash)
        
        tampered_payload = dict(payload)
        tampered_payload["details"] = {"status": "failed"}
        
        with self.assertRaises(AuditIntegrityError):
            AuditSecurityLayer.verify_record_integrity(tampered_payload, valid_hash)

    def test_policy_enforcement(self) -> None:
        from app.security.permissions import Role, Permission
        identity = IdentityContext(user_id="user_1", roles=frozenset([Role.OPERATOR]), _permissions=frozenset([Permission.DEPLOY]))
        
        SecurityPolicyEnforcer.check_operation_policy(identity, "deploy", "proj_1")
        
        with self.assertRaises(PolicyViolationError):
            SecurityPolicyEnforcer.check_operation_policy(identity, "delete", "proj_1")
            
        admin_identity = IdentityContext(user_id="admin_1", roles=frozenset([Role.ADMIN]), _permissions=frozenset([Permission.ARCHIVE]))
        SecurityPolicyEnforcer.check_operation_policy(admin_identity, "delete", "proj_1")


if __name__ == "__main__":
    unittest.main()
