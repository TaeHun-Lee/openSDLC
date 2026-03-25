"""Tests for EventBus — emit, subscribe, on_emit callback, close."""

from __future__ import annotations

import asyncio

import pytest

from app.services.event_bus import EventBus, EventType, RunEvent


@pytest.fixture()
def event_bus() -> EventBus:
    loop = asyncio.new_event_loop()
    bus = EventBus(loop=loop)
    yield bus
    loop.close()


def _make_event(event_type: EventType = EventType.LOG, **data) -> RunEvent:
    return RunEvent(event_type=event_type, data=data)


class TestEmit:
    def test_emit_appends(self, event_bus: EventBus):
        event_bus.emit(_make_event(message="hello"))
        assert len(event_bus) == 1
        assert event_bus.events[0].data["message"] == "hello"

    def test_on_emit_callback_called(self):
        captured: list[RunEvent] = []
        loop = asyncio.new_event_loop()
        bus = EventBus(loop=loop, on_emit=lambda e: captured.append(e))
        bus.emit(_make_event(message="test"))
        assert len(captured) == 1
        loop.close()

    def test_on_emit_exception_doesnt_break_emit(self):
        def bad_callback(e):
            raise RuntimeError("boom")

        loop = asyncio.new_event_loop()
        bus = EventBus(loop=loop, on_emit=bad_callback)
        bus.emit(_make_event(message="still works"))
        assert len(bus) == 1
        loop.close()


class TestSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_yields_existing_events(self):
        bus = EventBus()
        bus.emit(_make_event(message="a"))
        bus.emit(_make_event(message="b"))
        bus.close()

        results = []
        async for idx, event in bus.subscribe():
            results.append((idx, event.data["message"]))
        assert results == [(0, "a"), (1, "b")]

    @pytest.mark.asyncio
    async def test_subscribe_with_last_index(self):
        bus = EventBus()
        bus.emit(_make_event(message="skip"))
        bus.emit(_make_event(message="keep"))
        bus.close()

        results = []
        async for idx, event in bus.subscribe(last_index=1):
            results.append(event.data["message"])
        assert results == ["keep"]

    @pytest.mark.asyncio
    async def test_subscribe_timeout_yields_heartbeat(self):
        """Subscribe with short poll_interval yields None heartbeat on timeout."""
        bus = EventBus()

        async def consume():
            async for idx, event in bus.subscribe(poll_interval=0.05):
                if event is None:
                    continue  # skip heartbeat
                return event
            return None

        # Bus is open but empty — consumer should get heartbeats, then real event
        task = asyncio.create_task(consume())
        await asyncio.sleep(0.1)
        bus.emit(_make_event(message="arrived"))
        bus.close()
        result = await asyncio.wait_for(task, timeout=1.0)
        assert result is not None
        assert result.data["message"] == "arrived"

    @pytest.mark.asyncio
    async def test_heartbeat_is_none(self):
        """Heartbeat yields (index, None) when no events arrive before timeout."""
        bus = EventBus()

        heartbeat_received = False
        async for idx, event in bus.subscribe(poll_interval=0.02):
            if event is None:
                heartbeat_received = True
                bus.close()  # stop after first heartbeat
                break
        assert heartbeat_received


class TestEventTypes:
    def test_rework_triggered_type_exists(self):
        assert EventType.REWORK_TRIGGERED == "rework_triggered"

    def test_rework_event_to_sse(self):
        event = RunEvent(
            event_type=EventType.REWORK_TRIGGERED,
            data={
                "validator_step": 3,
                "rework_target": "ReqAgent",
                "rework_seq": 1,
                "iteration_num": 1,
                "validation_result": "fail",
                "message": "[ValidatorAgent] Rework triggered → ReqAgent (rework #1)",
            },
        )
        sse = event.to_sse(event_id=5)
        assert "id: 5" in sse
        assert "event: rework_triggered" in sse
        assert "ReqAgent" in sse

    def test_step_started_sse_contains_input_artifacts(self):
        event = RunEvent(
            event_type=EventType.STEP_STARTED,
            data={
                "step_num": 2,
                "agent_id": "CodeAgent",
                "iteration_num": 1,
                "rework_seq": 0,
                "input_artifacts": ["UseCaseModelArtifact"],
                "expected_output": "ImplementationArtifact",
                "mode": None,
                "message": "[CodeAgent] Step 2 started",
            },
        )
        sse = event.to_sse(event_id=10)
        assert "UseCaseModelArtifact" in sse
        assert "ImplementationArtifact" in sse

    def test_step_completed_sse_contains_output_artifact(self):
        event = RunEvent(
            event_type=EventType.STEP_COMPLETED,
            data={
                "step_num": 2,
                "agent_id": "CodeAgent",
                "iteration_num": 1,
                "output_artifact": "ImplementationArtifact",
                "model_used": "gemini-2.5-pro",
                "rework_seq": 0,
                "message": "[CodeAgent] Step 2 completed",
            },
        )
        sse = event.to_sse(event_id=11)
        assert "output_artifact" in sse
        assert "ImplementationArtifact" in sse


class TestClose:
    @pytest.mark.asyncio
    async def test_close_terminates_subscribe(self):
        bus = EventBus()
        bus.close()
        count = 0
        async for _ in bus.subscribe():
            count += 1
        assert count == 0
