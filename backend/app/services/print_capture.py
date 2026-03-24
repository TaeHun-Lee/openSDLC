"""Thread-local print() interception for capturing pipeline output.

Replaces builtins.print with an interceptor that routes output to a
per-thread callback while preserving normal stdout printing.
"""

from __future__ import annotations

import builtins
import json
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
def capture_prints(callback: Callable[[str], None], cancel_event: threading.Event | None = None):
    """Context manager: within this scope, print() calls also invoke callback(msg).

    Thread-safe — each thread has its own callback via threading.local().
    Optionally accepts a cancel_event for inter-step cancellation.
    """
    _thread_local.callback = callback
    _thread_local.cancel_event = cancel_event
    try:
        yield
    finally:
        _thread_local.callback = None
        _thread_local.cancel_event = None


def get_cancel_event() -> threading.Event | None:
    """Get the cancel event for the current thread (if any)."""
    return getattr(_thread_local, "cancel_event", None)


# --- Print message classifier ---

_AGENT_LINE_RE = re.compile(r"^\[(\w+(?:Agent)?)\]\s*(.+)")
_VERDICT_RE = re.compile(r"판정:\s*(PASS|WARNING|FAIL)", re.IGNORECASE)
_STEP_START_RE = re.compile(
    r"^\[__STEP_START__\]\s+step_num=(\d+)\s+agent=(\w+)\s+iteration=(\d+)\s+output=(\S+)"
)
_STEP_END_RE = re.compile(r"^\[__STEP_END__\]\s+(.+)$")


def classify_print_message(msg: str, step_ctx: dict | None = None) -> RunEvent:
    """Convert a captured print() message into a structured RunEvent.

    step_ctx is mutable dict carrying current {step_num, iteration_num, agent_name}
    across calls within the same run.
    """
    msg = msg.strip()
    if not msg:
        return RunEvent(event_type=EventType.LOG, data={"message": ""})

    ctx = step_ctx or {}

    # Step start marker — update context and emit STEP_STARTED
    step_start_match = _STEP_START_RE.match(msg)
    if step_start_match:
        ctx["step_num"] = int(step_start_match.group(1))
        ctx["agent_name"] = step_start_match.group(2)
        ctx["iteration_num"] = int(step_start_match.group(3))
        output_type = step_start_match.group(4)
        return RunEvent(
            event_type=EventType.STEP_STARTED,
            data={
                "step_num": ctx["step_num"],
                "agent_id": ctx["agent_name"],
                "iteration_num": ctx["iteration_num"],
                "output_type": output_type,
                "message": f"[{ctx['agent_name']}] Step {ctx['step_num']} started",
            },
        )

    # Step end marker — emit STEP_COMPLETED with full result data
    step_end_match = _STEP_END_RE.match(msg)
    if step_end_match:
        try:
            step_data = json.loads(step_end_match.group(1))
        except json.JSONDecodeError:
            step_data = {}
        ctx["step_num"] = step_data.get("step_num", ctx.get("step_num"))
        ctx["agent_name"] = step_data.get("agent_id", ctx.get("agent_name"))
        ctx["iteration_num"] = step_data.get("iteration_num", ctx.get("iteration_num"))
        return RunEvent(
            event_type=EventType.STEP_COMPLETED,
            data={
                **step_data,
                "message": f"[{ctx.get('agent_name')}] Step {ctx.get('step_num')} completed",
            },
        )

    # Inject current step context into data
    base_data: dict = {}
    if ctx.get("step_num") is not None:
        base_data["step_num"] = ctx["step_num"]
    if ctx.get("iteration_num") is not None:
        base_data["iteration_num"] = ctx["iteration_num"]

    # Pipeline lifecycle messages
    if msg.startswith("[Pipeline]") or msg.startswith("==="):
        if "시작" in msg:
            return RunEvent(event_type=EventType.PIPELINE_STARTED, data={**base_data, "message": msg})
        if "완료" in msg or "QUOTA" in msg or "ERROR" in msg:
            return RunEvent(event_type=EventType.PIPELINE_COMPLETED, data={**base_data, "message": msg})
        return RunEvent(event_type=EventType.LOG, data={**base_data, "message": msg})

    # Rate limit messages
    if msg.startswith("[Rate Limit]"):
        return RunEvent(event_type=EventType.LOG, data={**base_data, "message": msg})

    # Validation verdict
    verdict_match = _VERDICT_RE.search(msg)
    if verdict_match:
        return RunEvent(
            event_type=EventType.VALIDATION_RESULT,
            data={
                **base_data,
                "result": verdict_match.group(1).lower(),
                "agent_id": ctx.get("agent_name"),
                "message": msg,
            },
        )

    # Agent narrative
    agent_match = _AGENT_LINE_RE.match(msg)
    if agent_match:
        return RunEvent(
            event_type=EventType.AGENT_NARRATIVE,
            data={**base_data, "agent_id": agent_match.group(1), "message": msg},
        )

    # Artifact output messages
    if msg.startswith("[출력]") or msg.startswith("[실행]") or msg.startswith("[경고]"):
        return RunEvent(event_type=EventType.LOG, data={**base_data, "message": msg})

    return RunEvent(event_type=EventType.LOG, data={**base_data, "message": msg})


def make_event_callback(event_bus: EventBus) -> Callable[[str], None]:
    """Create a print callback that classifies messages and emits to an EventBus.

    Maintains per-run step context across calls.
    """
    step_ctx: dict = {}

    def callback(msg: str) -> None:
        event = classify_print_message(msg, step_ctx=step_ctx)
        event_bus.emit(event)

    return callback
