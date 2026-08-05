import time
from typing import Callable, TypeVar, Any
import logging

from app.reliability.exceptions import NonRetryableError, RetryExhaustedError
from app.reliability.models import RetryConfig

T = TypeVar("T")

class RetryManager:
    """Manages retries for transient operation failures."""

    def __init__(self, config: RetryConfig | None = None) -> None:
        self.config = config or RetryConfig()

    def execute_with_retry(self, operation: Callable[[], T], non_retryable_exceptions: tuple[type[Exception], ...] = (NonRetryableError,)) -> T:
        """
        Executes a callable, retrying it according to the configured backoff strategy.
        Raises RetryExhaustedError if max attempts are reached.
        """
        attempt = 1
        current_backoff = self.config.initial_backoff_sec

        while attempt <= self.config.max_attempts:
            try:
                return operation()
            except Exception as e:
                # Check if it is a non-retryable exception
                if isinstance(e, non_retryable_exceptions):
                    raise NonRetryableError(f"Operation failed with non-retryable error: {e}") from e

                if attempt == self.config.max_attempts:
                    raise RetryExhaustedError(
                        f"Operation failed after {self.config.max_attempts} attempts. Last error: {e}"
                    ) from e

                # Log retry intent here if logger was available (we keep it simple for now)
                time.sleep(current_backoff)
                
                # Calculate next backoff
                current_backoff = min(
                    current_backoff * self.config.backoff_multiplier,
                    self.config.max_backoff_sec
                )
                attempt += 1
                
        # Should never reach here due to the raise inside the loop
        raise RetryExhaustedError("Retry loop exited unexpectedly")
