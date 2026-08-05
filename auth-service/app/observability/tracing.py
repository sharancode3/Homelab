import contextvars
from contextlib import contextmanager
from typing import Generator

from app.observability.models import TraceContext

# ContextVar to store the current TraceContext for the running async task or thread
current_trace_context: contextvars.ContextVar[TraceContext | None] = contextvars.ContextVar(
    "current_trace_context", default=None
)


def get_current_trace() -> TraceContext | None:
    """Retrieve the active trace context if any."""
    return current_trace_context.get()


@contextmanager
def trace_scope(context: TraceContext | None = None) -> Generator[TraceContext, None, None]:
    """
    Context manager to set the trace context for a block of code.
    If no context is provided, a new one is created.
    """
    if context is None:
        context = TraceContext()
        
    token = current_trace_context.set(context)
    try:
        yield context
    finally:
        current_trace_context.reset(token)
