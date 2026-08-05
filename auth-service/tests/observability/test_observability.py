import io
import json
import unittest

from app.observability.logger import StructuredLogger
from app.observability.metrics import MetricsRegistry
from app.observability.models import TraceContext
from app.observability.tracing import get_current_trace, trace_scope


class ObservabilityTestCase(unittest.TestCase):
    def test_log_creation(self) -> None:
        sink = io.StringIO()
        logger = StructuredLogger(component="test_component")
        logger.sink = sink
        
        logger.info("test_event", "Testing log creation", project_id="proj_1")
        
        output = sink.getvalue()
        self.assertTrue(output)
        
        parsed = json.loads(output)
        self.assertEqual(parsed["severity"], "INFO")
        self.assertEqual(parsed["component"], "test_component")
        self.assertEqual(parsed["event_type"], "test_event")
        self.assertEqual(parsed["project_id"], "proj_1")

    def test_metric_recording(self) -> None:
        registry = MetricsRegistry()
        
        registry.increment_counter("test_counter", 5)
        self.assertEqual(registry.get_counter("test_counter"), 5)
        
        registry.record_duration("test_duration", 0.5)
        registry.record_duration("test_duration", 1.5)
        self.assertEqual(registry.get_average_duration("test_duration"), 1.0)
        
        with registry.measure_duration("test_context_duration"):
            pass
        self.assertTrue(registry.get_average_duration("test_context_duration") >= 0.0)

    def test_trace_propagation_and_correlation(self) -> None:
        context = TraceContext(correlation_id="corr_test_123")
        
        self.assertIsNone(get_current_trace())
        
        with trace_scope(context) as active_trace:
            self.assertEqual(active_trace.correlation_id, "corr_test_123")
            self.assertEqual(get_current_trace(), active_trace)
            
            # test propagation
            new_trace = active_trace.propagate("new_corr")
            self.assertEqual(new_trace.trace_id, active_trace.trace_id)
            self.assertEqual(new_trace.correlation_id, "new_corr")
            
        self.assertIsNone(get_current_trace())


if __name__ == "__main__":
    unittest.main()
