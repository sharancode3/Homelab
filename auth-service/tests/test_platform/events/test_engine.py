from app.storage.providers.sqlite import SQLiteProjectRepository, SQLiteAuditRepository, SQLiteOperationHistoryRepository
import unittest
from datetime import datetime, timezone

from app.platform.events.engine import EventEngine
from app.platform.events.enums import EventCategory, EventPriority, EventStatus


class EventEngineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = EventEngine()
        self.engine.register_route(EventCategory.LIFECYCLE, "lifecycle_handler")

    def test_event_creation_and_publishing(self) -> None:
        result = self.engine.publish(
            event_type="project_registered",
            category=EventCategory.LIFECYCLE,
            priority=EventPriority.NORMAL,
            payload={"project_id": "proj_123"},
            correlation_id="corr_abc",
            source_component="api_gateway",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.status, EventStatus.DELIVERED)
        self.assertIsNotNone(result.event_id)
        
        # Verify it was recorded
        recorded = self.engine._recorded_events.get(result.event_id)
        self.assertIsNotNone(recorded)
        if recorded:
            self.assertEqual(recorded.event_type, "project_registered")
            self.assertEqual(recorded.status, EventStatus.DELIVERED)

    def test_routing(self) -> None:
        result = self.engine.publish(
            event_type="project_registered",
            category=EventCategory.LIFECYCLE,
            priority=EventPriority.NORMAL,
            payload={"project_id": "proj_123"},
            correlation_id="corr_abc",
            source_component="api_gateway",
        )
        self.assertTrue(result.success)
        self.assertIn("lifecycle_handler", result.delivered_to)

    def test_explicit_routing(self) -> None:
        result = self.engine.publish(
            event_type="system_alert",
            category=EventCategory.SYSTEM,
            priority=EventPriority.HIGH,
            payload={"msg": "alert"},
            correlation_id="corr_xyz",
            source_component="monitor",
            target_identity="alert_manager",
        )
        self.assertTrue(result.success)
        self.assertIn("alert_manager", result.delivered_to)

    def test_recording(self) -> None:
        result = self.engine.publish(
            event_type="audit_log",
            category=EventCategory.AUDIT,
            priority=EventPriority.LOW,
            payload={"action": "login"},
            correlation_id="corr_111",
            source_component="auth",
        )
        self.assertTrue(result.success)
        self.assertIn(result.event_id, self.engine._recorded_events)

    def test_invalid_event_handling(self) -> None:
        result = self.engine.publish(
            event_type="",
            category=EventCategory.SYSTEM,
            priority=EventPriority.NORMAL,
            payload={},
            correlation_id="corr_abc",
            source_component="src",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.status, EventStatus.FAILED)
        self.assertIn("Event type is required", result.message)

    def test_correlation_id_handling(self) -> None:
        result = self.engine.publish(
            event_type="evt",
            category=EventCategory.SYSTEM,
            priority=EventPriority.NORMAL,
            payload={},
            correlation_id="",
            source_component="src",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.status, EventStatus.FAILED)
        self.assertIn("Correlation ID is required", result.message)
        
        # Valid correlation id
        result2 = self.engine.publish(
            event_type="evt",
            category=EventCategory.SYSTEM,
            priority=EventPriority.NORMAL,
            payload={},
            correlation_id="corr_valid",
            source_component="src",
        )
        self.assertTrue(result2.success)
        recorded = self.engine._recorded_events[result2.event_id]
        self.assertEqual(recorded.metadata.correlation_id, "corr_valid")

    def test_version_handling(self) -> None:
        result = self.engine.publish(
            event_type="evt",
            category=EventCategory.SYSTEM,
            priority=EventPriority.NORMAL,
            payload={},
            correlation_id="corr_abc",
            source_component="src",
            version="",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.status, EventStatus.FAILED)
        self.assertIn("Version is required", result.message)
        
        result2 = self.engine.publish(
            event_type="evt",
            category=EventCategory.SYSTEM,
            priority=EventPriority.NORMAL,
            payload={},
            correlation_id="corr_abc",
            source_component="src",
            version="2.0",
        )
        self.assertTrue(result2.success)
        recorded = self.engine._recorded_events[result2.event_id]
        self.assertEqual(recorded.metadata.version, "2.0")


if __name__ == "__main__":
    unittest.main()
