"""Tests for thread-local print capture context manager."""

from __future__ import annotations

import threading

from app.services.event_bus import EventType, RunEvent
from app.services.print_capture import (
    capture_prints,
    get_artifact_saver,
    get_cancel_event,
    get_event_emitter,
)


class TestCaptureContextManager:
    """capture_prints sets and clears thread-local callbacks."""

    def test_emitter_set_inside_context(self):
        events: list[RunEvent] = []
        emitter = lambda e: events.append(e)

        with capture_prints(event_emitter=emitter):
            got = get_event_emitter()
            assert got is emitter

    def test_emitter_cleared_after_context(self):
        with capture_prints(event_emitter=lambda e: None):
            pass
        assert get_event_emitter() is None

    def test_cancel_event_set_and_cleared(self):
        ev = threading.Event()
        with capture_prints(event_emitter=lambda e: None, cancel_event=ev):
            assert get_cancel_event() is ev
        assert get_cancel_event() is None

    def test_artifact_saver_set_and_cleared(self):
        saver = lambda it, ag, at, y: None
        with capture_prints(event_emitter=lambda e: None, artifact_saver=saver):
            assert get_artifact_saver() is saver
        assert get_artifact_saver() is None

    def test_cleanup_on_exception(self):
        """Thread-local state must be cleared even if the body raises."""
        try:
            with capture_prints(event_emitter=lambda e: None):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert get_event_emitter() is None
        assert get_cancel_event() is None
        assert get_artifact_saver() is None

    def test_emitter_callable_from_context(self):
        """Events emitted inside the context should be captured."""
        events: list[RunEvent] = []

        with capture_prints(event_emitter=lambda e: events.append(e)):
            emitter = get_event_emitter()
            emitter(RunEvent(event_type=EventType.LOG, data={"message": "hello"}))

        assert len(events) == 1
        assert events[0].data["message"] == "hello"


class TestThreadIsolation:
    """Each thread gets its own context — no cross-thread leaking."""

    def test_separate_threads_have_independent_context(self):
        results: dict[str, bool] = {}

        def worker(name: str, emitter):
            with capture_prints(event_emitter=emitter):
                got = get_event_emitter()
                results[name] = got is emitter

        e1 = lambda e: None
        e2 = lambda e: None
        t1 = threading.Thread(target=worker, args=("t1", e1))
        t2 = threading.Thread(target=worker, args=("t2", e2))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results["t1"] is True
        assert results["t2"] is True

    def test_main_thread_unaffected_by_child(self):
        """A child thread's context should not leak into the main thread."""
        assert get_event_emitter() is None

        def worker():
            with capture_prints(event_emitter=lambda e: None):
                pass

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        assert get_event_emitter() is None
