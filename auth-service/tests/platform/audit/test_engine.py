import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.platform.audit.engine import AuditEngine
from app.platform.audit.enums import AuditCategory, AuditSeverity, AuditStatus
from app.platform.audit.exceptions import AuditRecordError


class AuditEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = AuditEngine()

    def test_record_creation(self) -> None:
        record = self.engine.record_event(
            category=AuditCategory.LIFECYCLE,
            event_type="project_created",
            severity=AuditSeverity.INFO,
            source_component="api",
            outcome_status=AuditStatus.SUCCESS,
            summary="Project created successfully",
            target_identity="proj_123",
        )
        self.assertIsNotNone(record)
        self.assertEqual(record.audit_id[:4], "aud_")
        self.assertEqual(len(self.engine._records), 1)

    def test_integrity_verification(self) -> None:
        record = self.engine.record_event(
            category=AuditCategory.LIFECYCLE,
            event_type="project_created",
            severity=AuditSeverity.INFO,
            source_component="api",
            outcome_status=AuditStatus.SUCCESS,
            summary="Project created successfully",
            target_identity="proj_123",
        )
        
        self.assertTrue(self.engine.verify_integrity(record))
        
        # Tamper with the record (using dataclass replace since it's frozen)
        tampered_record = replace(record, summary="Tampered summary")
        
        self.assertFalse(self.engine.verify_integrity(tampered_record))

    def test_query_filtering(self) -> None:
        # Create some records
        t1 = datetime.now(timezone.utc) - timedelta(hours=2)
        
        # We manipulate the timestamp internally to test time filtering
        r1 = self.engine.record_event(
            category=AuditCategory.SECURITY,
            event_type="login",
            severity=AuditSeverity.INFO,
            source_component="auth",
            outcome_status=AuditStatus.SUCCESS,
            summary="User logged in",
            target_identity="user_1",
            correlation_id="corr_1",
        )
        
        r2 = self.engine.record_event(
            category=AuditCategory.LIFECYCLE,
            event_type="deploy",
            severity=AuditSeverity.INFO,
            source_component="deployer",
            outcome_status=AuditStatus.FAILURE,
            summary="Deployment failed",
            target_identity="proj_2",
            correlation_id="corr_2",
        )
        
        # Manually alter the timestamp of the first record for querying
        self.engine._records[0] = replace(self.engine._records[0], timestamp=t1)
        
        # Query by project
        proj_results = self.engine.query(project_id="proj_2")
        self.assertEqual(len(proj_results), 1)
        self.assertEqual(proj_results[0].target_identity, "proj_2")
        
        # Query by category
        cat_results = self.engine.query(category=AuditCategory.SECURITY)
        self.assertEqual(len(cat_results), 1)
        self.assertEqual(cat_results[0].category, AuditCategory.SECURITY)
        
        # Query by correlation ID
        corr_results = self.engine.query(correlation_id="corr_1")
        self.assertEqual(len(corr_results), 1)
        
        # Query by time
        time_results = self.engine.query(start_time=datetime.now(timezone.utc) - timedelta(hours=1))
        self.assertEqual(len(time_results), 1)
        self.assertEqual(time_results[0].audit_id, r2.audit_id)

    def test_failed_record_handling(self) -> None:
        with self.assertRaises(AuditRecordError):
            self.engine.record_event(
                category=AuditCategory.LIFECYCLE,
                event_type="",
                severity=AuditSeverity.INFO,
                source_component="api",
                outcome_status=AuditStatus.SUCCESS,
                summary="Project created successfully",
            )
            
    def test_correlation_tracking(self) -> None:
        record = self.engine.record_event(
            category=AuditCategory.SYSTEM,
            event_type="sys_start",
            severity=AuditSeverity.INFO,
            source_component="sys",
            outcome_status=AuditStatus.SUCCESS,
            summary="System started",
            correlation_id="startup_123",
        )
        
        results = self.engine.query(correlation_id="startup_123")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].audit_id, record.audit_id)


if __name__ == "__main__":
    unittest.main()
