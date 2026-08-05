import unittest

from app.reliability.exceptions import NonRetryableError, RetryExhaustedError
from app.reliability.models import RetryConfig
from app.reliability.queue import DeadLetterQueue, EventReliabilityManager
from app.reliability.recovery import OperationRecoveryManager
from app.reliability.retry import RetryManager


class ReliabilityTestCase(unittest.TestCase):
    def test_retry_success_after_failure(self) -> None:
        manager = RetryManager(RetryConfig(max_attempts=3, initial_backoff_sec=0.01))
        
        attempts = 0
        def flappy_operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise Exception("temporary failure")
            return "success"
            
        result = manager.execute_with_retry(flappy_operation)
        self.assertEqual(result, "success")
        self.assertEqual(attempts, 3)

    def test_retry_exhaustion(self) -> None:
        manager = RetryManager(RetryConfig(max_attempts=2, initial_backoff_sec=0.01))
        
        def failing_operation() -> str:
            raise Exception("persistent failure")
            
        with self.assertRaises(RetryExhaustedError):
            manager.execute_with_retry(failing_operation)

    def test_non_retryable_failure(self) -> None:
        manager = RetryManager(RetryConfig(max_attempts=3, initial_backoff_sec=0.01))
        
        attempts = 0
        def fatal_operation() -> str:
            nonlocal attempts
            attempts += 1
            raise NonRetryableError("fatal config error")
            
        with self.assertRaises(NonRetryableError):
            manager.execute_with_retry(fatal_operation)
            
        self.assertEqual(attempts, 1)

    def test_recovery_record_creation(self) -> None:
        recovery = OperationRecoveryManager()
        
        record = recovery.capture_failure(
            operation_id="op_1",
            project_id="proj_1",
            operation_type="deploy",
            error_message="failed at step 2",
            context_payload={"user": "admin"}
        )
        
        self.assertEqual(record.operation_id, "op_1")
        self.assertFalse(record.resolved)
        
        retrieved = recovery.get_record("op_1")
        self.assertIsNotNone(retrieved)
        if retrieved:
            self.assertEqual(retrieved.error_message, "failed at step 2")

    def test_failed_event_handling(self) -> None:
        dlq = DeadLetterQueue()
        event_rel = EventReliabilityManager(dlq)
        
        event_rel.handle_delivery_failure("user_created", {"id": 1}, Exception("network timeout"))
        
        events = dlq.get_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].original_event_type, "user_created")
        self.assertEqual(events[0].reason, "network timeout")


if __name__ == "__main__":
    unittest.main()
