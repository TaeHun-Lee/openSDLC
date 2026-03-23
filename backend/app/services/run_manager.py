"""Pipeline run lifecycle manager.

Manages concurrent pipeline runs in background threads,
bridging print() output to SSE event streams.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.core.config import PIPELINES_DIR
from app.core.llm_client import QuotaExhaustedError
from app.core.pipeline.graph_builder import load_pipeline_definition, run_pipeline
from app.services.event_bus import EventBus, EventType, RunEvent
from app.services.print_capture import capture_prints, make_event_callback

logger = logging.getLogger(__name__)


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RunRecord:
    """In-memory record for a single pipeline run."""

    run_id: str
    pipeline_name: str
    user_story: str
    max_iterations: int
    status: RunStatus
    event_bus: EventBus
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    final_state: dict | None = None  # PipelineState dict
    error: str | None = None


class RunManager:
    """Manages pipeline run lifecycle with concurrency control."""

    def __init__(self, max_concurrent: int = 2) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent)

    def get_run(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[RunRecord]:
        return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)

    async def start_run(
        self,
        pipeline_name: str,
        user_story: str,
        max_iterations: int = 3,
    ) -> RunRecord:
        """Start a pipeline run in the background. Returns immediately."""
        run_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        event_bus = EventBus(loop=loop)

        record = RunRecord(
            run_id=run_id,
            pipeline_name=pipeline_name,
            user_story=user_story,
            max_iterations=max_iterations,
            status=RunStatus.PENDING,
            event_bus=event_bus,
        )
        self._runs[run_id] = record

        asyncio.create_task(self._execute_run(record))
        return record

    async def _execute_run(self, record: RunRecord) -> None:
        """Acquire semaphore, run pipeline in thread, emit events."""
        async with self._semaphore:
            record.status = RunStatus.RUNNING
            record.event_bus.emit(
                RunEvent(
                    event_type=EventType.PIPELINE_STARTED,
                    data={
                        "run_id": record.run_id,
                        "pipeline": record.pipeline_name,
                        "message": f"Pipeline '{record.pipeline_name}' starting",
                    },
                )
            )

            callback = make_event_callback(record.event_bus)

            def _run_sync() -> dict:
                with capture_prints(callback):
                    pipeline_path = PIPELINES_DIR / f"{record.pipeline_name}.yaml"
                    if not pipeline_path.is_file():
                        # Try as absolute/relative path
                        pipeline_path = Path(record.pipeline_name)
                    pipeline_def = load_pipeline_definition(pipeline_path)
                    pipeline_def.max_iterations = record.max_iterations
                    return run_pipeline(pipeline_def, record.user_story)

            try:
                final_state = await asyncio.to_thread(_run_sync)
                record.final_state = dict(final_state)
                record.status = RunStatus.COMPLETED
                record.finished_at = time.time()

                pipeline_status = final_state.get("pipeline_status", "unknown")
                record.event_bus.emit(
                    RunEvent(
                        event_type=EventType.PIPELINE_COMPLETED,
                        data={
                            "run_id": record.run_id,
                            "pipeline_status": pipeline_status,
                            "steps_completed": len(final_state.get("steps_completed", [])),
                            "iteration_count": final_state.get("iteration_count", 0),
                        },
                    )
                )
            except QuotaExhaustedError as exc:
                record.status = RunStatus.FAILED
                record.finished_at = time.time()
                record.error = str(exc)
                record.event_bus.emit(
                    RunEvent(
                        event_type=EventType.PIPELINE_ERROR,
                        data={"run_id": record.run_id, "error": str(exc), "type": "quota_exhausted"},
                    )
                )
            except Exception as exc:
                record.status = RunStatus.FAILED
                record.finished_at = time.time()
                record.error = f"{type(exc).__name__}: {exc}"
                logger.exception("Pipeline run %s failed", record.run_id)
                record.event_bus.emit(
                    RunEvent(
                        event_type=EventType.PIPELINE_ERROR,
                        data={"run_id": record.run_id, "error": record.error},
                    )
                )
            finally:
                record.event_bus.close()
