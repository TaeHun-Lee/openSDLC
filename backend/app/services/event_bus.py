"""Per-run event queue with async consumer support for SSE streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    PIPELINE_STARTED = "pipeline_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    VALIDATION_RESULT = "validation_result"
    AGENT_NARRATIVE = "agent_narrative"
    PIPELINE_COMPLETED = "pipeline_completed"
    REWORK_TRIGGERED = "rework_triggered"
    PIPELINE_ERROR = "pipeline_error"
    PIPELINE_WARNING = "pipeline_warning"
    LOG = "log"


@dataclass
class RunEvent:
    event_type: EventType
    data: dict
    timestamp: float = field(default_factory=time.time)

    def to_sse(self, event_id: int) -> str:
        """Format as SSE text block."""
        payload = {
            "id": event_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp,
        }
        return f"id: {event_id}\nevent: {self.event_type.value}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class EventBus:
    """Thread-safe event accumulator with async SSE consumer support.

    - emit() is called from the synchronous pipeline thread.
    - subscribe() is an async generator consumed by the SSE endpoint.
    - Uses loop.call_soon_threadsafe() to bridge threads safely.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop | None = None,
        on_emit: Callable[[RunEvent], None] | None = None,
    ) -> None:
        self._events: list[RunEvent] = []
        self._loop = loop or asyncio.get_event_loop()
        self._notify: asyncio.Event = asyncio.Event()
        self._closed = False
        self._on_emit = on_emit

    def emit(self, event: RunEvent) -> None:
        """Append event and wake up SSE consumers. Thread-safe."""
        self._events.append(event)
        if self._on_emit is not None:
            try:
                self._on_emit(event)
            except Exception:
                logger.exception("on_emit callback error")
        try:
            self._loop.call_soon_threadsafe(self._notify.set)
        except RuntimeError:
            pass  # loop closed

    def close(self) -> None:
        """Signal that no more events will be emitted."""
        self._closed = True
        try:
            self._loop.call_soon_threadsafe(self._notify.set)
        except RuntimeError:
            pass

    def clear(self) -> None:
        """Release accumulated events to free memory.

        Should be called after the run is fully persisted to DB and all
        SSE subscribers have disconnected.
        """
        self._events.clear()

    @property
    def events(self) -> list[RunEvent]:
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)

    async def subscribe(
        self, last_index: int = 0, poll_interval: float = 1.5,
    ) -> AsyncIterator[tuple[int, RunEvent | None]]:
        """Async generator yielding (index, event) tuples.

        Yields all events from last_index onward, then waits for new events.
        Terminates when the bus is closed and all events have been yielded.

        On poll_interval timeout with no new events, yields (current_index, None)
        as a heartbeat signal so callers can perform disconnect detection.
        """
        idx = last_index
        while True:
            # Yield any buffered events
            while idx < len(self._events):
                yield idx, self._events[idx]
                idx += 1

            # If closed and caught up, we're done
            if self._closed:
                return

            # Wait for new events with timeout so callers can check disconnect
            self._notify.clear()
            try:
                await asyncio.wait_for(self._notify.wait(), timeout=poll_interval)
            except asyncio.TimeoutError:
                # Yield heartbeat (None) so caller can run disconnect check
                yield idx, None
