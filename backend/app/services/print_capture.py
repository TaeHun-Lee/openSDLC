"""Thread-local print() interception for capturing pipeline output.

Replaces builtins.print with an interceptor that routes output to a
per-thread callback while preserving normal stdout printing.
"""

from __future__ import annotations

import builtins
import re
import threading
from collections.abc import Callable
from contextlib import contextmanager

from app.services.event_bus import EventBus, EventType, RunEvent

_thread_local = threading.local()
_original_print = builtins.print
_installed = False


def _intercepted_print(*args, **kwargs) -> None:
    """Replacement for builtins.print that also invokes per-thread callback."""
    callback: Callable[[str], None] | None = getattr(_thread_local, "callback", None)
    if callback is not None:
        message = " ".join(str(a) for a in args)
        try:
            callback(message)
        except Exception:
            pass  # never break the pipeline due to callback failure
    _original_print(*args, **kwargs)


def install_print_hook() -> None:
    """Install the global print interceptor (idempotent)."""
    global _installed
    if not _installed:
        builtins.print = _intercepted_print
        _installed = True


def uninstall_print_hook() -> None:
    """Restore original print (for testing)."""
    global _installed
    builtins.print = _original_print
    _installed = False


@contextmanager
def capture_prints(callback: Callable[[str], None]):
    """Context manager: within this scope, print() calls also invoke callback(msg).

    Thread-safe — each thread has its own callback via threading.local().
    """
    _thread_local.callback = callback
    try:
        yield
    finally:
        _thread_local.callback = None


# --- Print message classifier ---

_AGENT_LINE_RE = re.compile(r"^\[(\w+(?:Agent)?)\]\s*(.+)")
_VERDICT_RE = re.compile(r"판정:\s*(PASS|WARNING|FAIL)", re.IGNORECASE)


def classify_print_message(msg: str) -> RunEvent:
    """Convert a captured print() message into a structured RunEvent."""
    msg = msg.strip()
    if not msg:
        return RunEvent(event_type=EventType.LOG, data={"message": ""})

    # Pipeline lifecycle messages
    if msg.startswith("[Pipeline]") or msg.startswith("==="):
        if "시작" in msg:
            return RunEvent(event_type=EventType.PIPELINE_STARTED, data={"message": msg})
        if "완료" in msg or "QUOTA" in msg or "ERROR" in msg:
            return RunEvent(event_type=EventType.PIPELINE_COMPLETED, data={"message": msg})
        return RunEvent(event_type=EventType.LOG, data={"message": msg})

    # Rate limit messages
    if msg.startswith("[Rate Limit]"):
        return RunEvent(event_type=EventType.LOG, data={"message": msg})

    # Validation verdict
    verdict_match = _VERDICT_RE.search(msg)
    if verdict_match:
        return RunEvent(
            event_type=EventType.VALIDATION_RESULT,
            data={"result": verdict_match.group(1).lower(), "message": msg},
        )

    # Agent narrative
    agent_match = _AGENT_LINE_RE.match(msg)
    if agent_match:
        return RunEvent(
            event_type=EventType.AGENT_NARRATIVE,
            data={"agent_id": agent_match.group(1), "message": msg},
        )

    # Artifact output messages
    if msg.startswith("[출력]") or msg.startswith("[실행]") or msg.startswith("[경고]"):
        return RunEvent(event_type=EventType.LOG, data={"message": msg})

    return RunEvent(event_type=EventType.LOG, data={"message": msg})


def make_event_callback(event_bus: EventBus) -> Callable[[str], None]:
    """Create a print callback that classifies messages and emits to an EventBus."""

    def callback(msg: str) -> None:
        event = classify_print_message(msg)
        event_bus.emit(event)

    return callback
