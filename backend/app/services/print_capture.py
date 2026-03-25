"""Thread-local context for pipeline execution.

Provides per-thread event emitter, cancel event, and artifact saver
via threading.local(). The pipeline thread sets these before execution
and generic_agent nodes use the getters to emit structured events
without relying on print() interception.

Print output is still forwarded to stdout for terminal logging, but
event routing is handled by direct callback invocation — no regex parsing.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from app.services.event_bus import RunEvent

_thread_local = threading.local()

# Type alias for the event emitter callback
EventEmitter = Callable[[RunEvent], None]


# ---------------------------------------------------------------------------
# Context manager — sets up per-thread callbacks for a pipeline run
# ---------------------------------------------------------------------------

from contextlib import contextmanager  # noqa: E402


@contextmanager
def capture_prints(
    event_emitter: EventEmitter,
    cancel_event: threading.Event | None = None,
    artifact_saver: Callable[[int, str, str, str], None] | None = None,
):
    """Set up thread-local pipeline context for the duration of a run.

    Args:
        event_emitter: Callback that receives structured RunEvent objects.
        cancel_event: Threading event for inter-step cancellation.
        artifact_saver: Callback for immediate artifact disk persistence.
    """
    _thread_local.event_emitter = event_emitter
    _thread_local.cancel_event = cancel_event
    _thread_local.artifact_saver = artifact_saver
    try:
        yield
    finally:
        _thread_local.event_emitter = None
        _thread_local.cancel_event = None
        _thread_local.artifact_saver = None


# ---------------------------------------------------------------------------
# Getters — called from generic_agent nodes
# ---------------------------------------------------------------------------


def get_event_emitter() -> EventEmitter | None:
    """Get the event emitter for the current thread (if any)."""
    return getattr(_thread_local, "event_emitter", None)


def get_cancel_event() -> threading.Event | None:
    """Get the cancel event for the current thread (if any)."""
    return getattr(_thread_local, "cancel_event", None)


def get_artifact_saver() -> Callable[[int, str, str, str], None] | None:
    """Get the artifact saver callback for the current thread (if any).

    Signature: (iteration_num, agent_id, artifact_type, artifact_yaml) -> None
    """
    return getattr(_thread_local, "artifact_saver", None)
