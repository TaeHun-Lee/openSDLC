"""Pipeline run lifecycle manager.

Manages concurrent pipeline runs in background threads,
bridging print() output to SSE event streams.
Persists runs, events, artifacts, and code files to SQLite + filesystem.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.core.artifacts.code_extractor import write_code_files
from app.core.artifacts.parser import extract_artifact_id
from app.core.config import PIPELINES_DIR, RUNS_DIR
from app.core.llm_client import QuotaExhaustedError
from app.core.pipeline.graph_builder import load_pipeline_definition, run_pipeline
from app.db import repository as repo
from app.db.models import Event as EventModel
from app.services.event_bus import EventBus, EventType, RunEvent
from app.services.print_capture import capture_prints, make_event_callback

logger = logging.getLogger(__name__)


class CancelledError(Exception):
    """Raised when a pipeline run is cancelled by user."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run '{run_id}' cancelled")
        self.run_id = run_id


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RunRecord:
    """In-memory record for a single pipeline run (active runs only)."""

    run_id: str
    pipeline_name: str
    user_story: str
    max_iterations: int
    status: RunStatus
    event_bus: EventBus
    project_id: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    final_state: dict | None = None  # PipelineState dict
    error: str | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    # Real-time step tracking for progress queries
    current_iteration: int = 1
    current_step: int | None = None
    current_agent: str | None = None
    steps_total: int | None = None


class RunManager:
    """Manages pipeline run lifecycle with concurrency control and DB persistence."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        max_concurrent: int = 2,
    ) -> None:
        self._active_runs: dict[str, RunRecord] = {}
        self._session_factory = session_factory
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent)

    # ------------------------------------------------------------------
    # Read helpers (check in-memory first, then DB)
    # ------------------------------------------------------------------

    def get_run(self, run_id: str) -> RunRecord | None:
        """Get active in-memory run record (for SSE streaming)."""
        return self._active_runs.get(run_id)

    def get_run_from_db(self, run_id: str):
        """Get run from DB (for completed runs)."""
        with self._session_factory() as session:
            return repo.get_run(session, run_id)

    def list_runs_from_db(self, project_id: str | None = None):
        """List all runs from DB."""
        with self._session_factory() as session:
            return repo.list_runs(session, project_id=project_id)

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    def cancel_run(self, run_id: str) -> bool:
        """Request cancellation of an active run. Returns True if the run was found."""
        record = self._active_runs.get(run_id)
        if record is None or record.status not in (RunStatus.PENDING, RunStatus.RUNNING):
            return False
        record.cancel_event.set()
        return True

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    async def start_run(
        self,
        pipeline_name: str,
        user_story: str,
        max_iterations: int = 3,
        project_id: str | None = None,
    ) -> RunRecord:
        """Start a pipeline run in the background. Returns immediately."""
        run_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()

        # Persist to DB
        with self._session_factory() as session:
            repo.create_run(
                session,
                run_id=run_id,
                pipeline_name=pipeline_name,
                user_story=user_story,
                max_iterations=max_iterations,
                project_id=project_id,
            )

        record = RunRecord(
            run_id=run_id,
            pipeline_name=pipeline_name,
            user_story=user_story,
            max_iterations=max_iterations,
            status=RunStatus.PENDING,
            event_bus=EventBus(
                loop=loop,
                on_emit=self._make_realtime_db_callback(run_id),
            ),
            project_id=project_id,
        )
        self._active_runs[run_id] = record

        asyncio.create_task(self._execute_run(record))
        return record

    def _make_realtime_db_callback(self, run_id: str):
        """Create an on_emit callback that persists iteration/step to DB in real time."""
        iterations_created: set[int] = set()
        step_counter_per_iter: dict[int, int] = {}

        def _on_emit(event: RunEvent) -> None:
            record = self._active_runs.get(run_id)

            if event.event_type == EventType.STEP_STARTED:
                data = event.data
                iter_num = data.get("iteration_num", 1)
                agent_id = data.get("agent_id", "")

                # Update in-memory progress tracking
                if record:
                    record.current_iteration = iter_num
                    record.current_step = data.get("step_num")
                    record.current_agent = agent_id

                # Create iteration row if first step
                if iter_num not in iterations_created:
                    with self._session_factory() as session:
                        repo.create_iteration(
                            session,
                            run_id=run_id,
                            iteration_num=iter_num,
                            started_at=event.timestamp,
                        )
                    iterations_created.add(iter_num)

                # Create step row
                step_num_in_iter = step_counter_per_iter.get(iter_num, 0) + 1
                step_counter_per_iter[iter_num] = step_num_in_iter
                with self._session_factory() as session:
                    repo.create_step(
                        session,
                        run_id=run_id,
                        iteration_num=iter_num,
                        step_num=step_num_in_iter,
                        agent_name=agent_id,
                        mode=data.get("mode"),
                        started_at=event.timestamp,
                    )

            elif event.event_type == EventType.STEP_COMPLETED:
                data = event.data
                iter_num = data.get("iteration_num", 1)
                step_num_in_iter = step_counter_per_iter.get(iter_num, 1)

                with self._session_factory() as session:
                    repo.update_step(
                        session, run_id, iter_num, step_num_in_iter,
                        verdict=data.get("validation_result"),
                        model_used=data.get("model_used"),
                        provider=data.get("provider"),
                        input_tokens=data.get("input_tokens"),
                        output_tokens=data.get("output_tokens"),
                        cache_read_tokens=data.get("cache_read_tokens"),
                        cache_creation_tokens=data.get("cache_creation_tokens"),
                        finished_at=data.get("finished_at"),
                    )

        return _on_emit

    async def _execute_run(self, record: RunRecord) -> None:
        """Acquire semaphore, run pipeline in thread, emit events, persist results."""
        async with self._semaphore:
            record.status = RunStatus.RUNNING
            with self._session_factory() as session:
                repo.update_run_status(session, record.run_id, "running")

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

            # Resolve pipeline to get step count for progress tracking
            pipeline_path = PIPELINES_DIR / f"{record.pipeline_name}.yaml"
            if not pipeline_path.is_file():
                pipeline_path = Path(record.pipeline_name)
            pipeline_def = load_pipeline_definition(pipeline_path)
            pipeline_def.max_iterations = record.max_iterations
            record.steps_total = len(pipeline_def.steps)

            callback = make_event_callback(record.event_bus)

            def _run_sync() -> dict:
                # Check cancellation before starting
                if record.cancel_event.is_set():
                    raise CancelledError(record.run_id)
                with capture_prints(callback, cancel_event=record.cancel_event):
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

                # Persist remaining data (artifacts, code files, events) to DB + filesystem
                await asyncio.to_thread(
                    self._persist_completed_run, record
                )

            except (CancelledError, InterruptedError):
                record.status = RunStatus.CANCELLED
                record.finished_at = time.time()
                record.error = "Run cancelled by user"
                record.event_bus.emit(
                    RunEvent(
                        event_type=EventType.PIPELINE_ERROR,
                        data={"run_id": record.run_id, "error": record.error, "type": "cancelled"},
                    )
                )
                with self._session_factory() as session:
                    repo.update_run_status(
                        session, record.run_id, "cancelled",
                        finished_at=record.finished_at, error=record.error,
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
                with self._session_factory() as session:
                    repo.update_run_status(
                        session, record.run_id, "failed",
                        finished_at=record.finished_at, error=record.error,
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
                with self._session_factory() as session:
                    repo.update_run_status(
                        session, record.run_id, "failed",
                        finished_at=record.finished_at, error=record.error,
                    )
            finally:
                record.event_bus.close()
                # Clean up active run from memory
                self._active_runs.pop(record.run_id, None)

    # ------------------------------------------------------------------
    # Post-run persistence (called from thread)
    # ------------------------------------------------------------------

    def _persist_completed_run(self, record: RunRecord) -> None:
        """Persist remaining data from a completed run to DB and filesystem.

        Iterations and steps are already created in real time via the on_emit callback.
        This method handles: run status update, artifacts, code files, events, and
        iteration finalization (satisfaction scores, finished_at).
        """
        final_state = record.final_state
        if not final_state:
            return

        run_id = record.run_id
        steps_completed = final_state.get("steps_completed", [])

        with self._session_factory() as session:
            # 1) Update run status in DB
            repo.update_run_status(
                session, run_id, "completed",
                finished_at=record.finished_at,
            )

            # 2) Save artifacts and update iteration metadata
            iterations_seen: set[int] = set()
            step_counter_per_iter: dict[int, int] = {}

            for sr in steps_completed:
                iter_num = sr.get("iteration_num", 1)
                step_num_in_iter = step_counter_per_iter.get(iter_num, 0) + 1
                step_counter_per_iter[iter_num] = step_num_in_iter
                iterations_seen.add(iter_num)

                # Update step with rework_seq (not available at STEP_STARTED time)
                rework_seq = sr.get("rework_seq", 0)
                if rework_seq:
                    repo.update_step(
                        session, run_id, iter_num, step_num_in_iter,
                        rework_seq=rework_seq,
                    )

                # Save artifact YAML to filesystem
                artifact_yaml = sr.get("artifact_yaml", "")
                if artifact_yaml:
                    artifact_type = sr.get("artifact_type", "unknown")
                    artifact_id = extract_artifact_id(artifact_yaml)
                    file_path = self._save_artifact_file(
                        run_id, iter_num, step_num_in_iter, artifact_type, artifact_yaml,
                    )
                    repo.insert_artifact(
                        session,
                        run_id=run_id,
                        iteration_num=iter_num,
                        step_num=step_num_in_iter,
                        agent_name=sr["agent_id"],
                        artifact_type=artifact_type,
                        artifact_id=artifact_id,
                        file_path=str(file_path),
                    )

                # PMAgent satisfaction score → update iteration
                if sr.get("satisfaction_score") is not None and sr["agent_id"] == "PMAgent":
                    repo.update_iteration(
                        session, run_id, iter_num,
                        satisfaction_score=sr["satisfaction_score"],
                    )

            # 3) Finalize iterations
            for iter_num in iterations_seen:
                iter_steps = [
                    s for s in steps_completed
                    if s.get("iteration_num", 1) == iter_num
                ]
                last_finished = max(
                    (s.get("finished_at", 0) for s in iter_steps), default=None
                )
                repo.update_iteration(
                    session, run_id, iter_num,
                    status="completed",
                    finished_at=last_finished,
                )

            # 4) Extract and save code files for each iteration
            self._persist_code_files(session, run_id, steps_completed)

            # 5) Persist events from EventBus
            self._persist_events(session, record)

    def _save_artifact_file(
        self,
        run_id: str,
        iteration_num: int,
        step_num: int,
        artifact_type: str,
        yaml_content: str,
    ) -> Path:
        """Write artifact YAML to filesystem, return the path."""
        artifact_dir = RUNS_DIR / run_id / f"iteration-{iteration_num:02d}" / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{step_num:03d}_{artifact_type}.yaml"
        file_path = artifact_dir / filename
        file_path.write_text(yaml_content, encoding="utf-8")
        return file_path

    def _persist_code_files(
        self,
        session: Session,
        run_id: str,
        steps_completed: list[dict],
    ) -> None:
        """Extract code files from ImplementationArtifact and save to filesystem."""
        # Group by iteration — use the latest ImplementationArtifact per iteration
        impl_per_iter: dict[int, str] = {}
        for sr in steps_completed:
            if sr.get("artifact_type", "").startswith("ImplementationArtifact"):
                iter_num = sr.get("iteration_num", 1)
                impl_per_iter[iter_num] = sr.get("artifact_yaml", "")

        for iter_num, impl_yaml in impl_per_iter.items():
            if not impl_yaml:
                continue
            workspace_dir = RUNS_DIR / run_id / f"iteration-{iter_num:02d}" / "workspace"
            written = write_code_files(impl_yaml, workspace_dir)
            for fpath in written:
                rel = str(fpath.relative_to(workspace_dir))
                repo.insert_code_file(
                    session,
                    run_id=run_id,
                    iteration_num=iter_num,
                    relative_path=rel,
                    file_path=str(fpath),
                    size_bytes=fpath.stat().st_size,
                )

    def _persist_events(self, session: Session, record: RunRecord) -> None:
        """Batch-persist all EventBus events to DB."""
        events = record.event_bus.events
        if not events:
            return

        db_events: list[EventModel] = []
        # Step context is tracked by STEP_STARTED events emitted from generic_agent
        current_iteration = 1
        current_step: int | None = None
        current_agent: str | None = None

        for evt in events:
            data = evt.data or {}

            # STEP_STARTED carries authoritative step/iteration context
            if evt.event_type == EventType.STEP_STARTED:
                current_step = data.get("step_num")
                current_iteration = data.get("iteration_num", current_iteration)
                current_agent = data.get("agent_id")
            else:
                # Use embedded context from print_capture if available
                if "iteration_num" in data:
                    current_iteration = data["iteration_num"]
                if "step_num" in data:
                    current_step = data["step_num"]
                agent_name = data.get("agent_id") or current_agent
                if evt.event_type in (EventType.AGENT_NARRATIVE, EventType.VALIDATION_RESULT):
                    current_agent = agent_name

            db_events.append(EventModel(
                run_id=record.run_id,
                iteration_num=current_iteration,
                step_num=current_step,
                agent_name=data.get("agent_id") or current_agent,
                event_type=evt.event_type.value,
                message=data.get("message", ""),
                data=json.dumps(data, ensure_ascii=False) if data else None,
                created_at=evt.timestamp,
            ))

        repo.bulk_insert_events(session, db_events)
