import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Generator


class MetricsRegistry:
    """A simple in-memory metrics registry for tracking platform health."""

    def __init__(self) -> None:
        self.counters: dict[str, int] = defaultdict(int)
        self.durations: dict[str, list[float]] = defaultdict(list)

    def increment_counter(self, metric_name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        self.counters[metric_name] += value

    def record_duration(self, metric_name: str, duration_sec: float) -> None:
        """Record a duration/latency metric."""
        self.durations[metric_name].append(duration_sec)

    @contextmanager
    def measure_duration(self, metric_name: str) -> Generator[None, None, None]:
        """Context manager to automatically measure and record duration."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            self.record_duration(metric_name, duration)

    def get_counter(self, metric_name: str) -> int:
        return self.counters.get(metric_name, 0)
        
    def get_average_duration(self, metric_name: str) -> float:
        times = self.durations.get(metric_name)
        if not times:
            return 0.0
        return sum(times) / len(times)


# Global singleton registry for simplicity in this phase
default_registry = MetricsRegistry()
