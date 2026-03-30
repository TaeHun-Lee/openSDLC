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

from app.core.artifacts.code_extractor import write_code_blocks
from app.core.artifacts.parser import extract_artifact_id
from app.core.config import PIPELINES_DIR, get_runs_dir
from app.core.llm_client import QuotaExhaustedError
from app.core.pipeline.graph_builder import load_pipeline_definition, resume_pipeline, run_pipeline
from app.core.pipeline.state import PipelineState, StepResult
from app.db import repository as repo
from app.db.models import Event as EventModel
from app.services.event_bus import EventBus, EventType, RunEvent
from app.services.print_capture import capture_prints

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
    # Webhook notification
    webhook_url: str | None = None
    webhook_events: list[str] | None = None  # e.g. ["completed", "failed"]
    # Resume support — explicitly declared instead of dynamic attributes
    artifact_saver: object | None = None  # Callable for saving artifacts
    restored_state: dict | None = None  # PipelineState dict for resume


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
    # Resume
    # ------------------------------------------------------------------

    def _restore_pipeline_state(self, run_id: str) -> PipelineState:
        """Restore PipelineState from DB for a previously interrupted run.

        Reads completed steps and their artifacts from DB, reconstructing the
        state dict that LangGraph needs to resume execution.
        """
        with self._session_factory() as session:
            db_run = repo.get_run(session, run_id)
            if db_run is None:
                raise ValueError(f"Run '{run_id}' not found in DB")

            db_steps = repo.get_steps_for_run(session, run_id)

            # Rebuild steps_completed list
            steps_completed: list[StepResult] = []
            latest_artifacts: dict[str, str] = {}
            last_iteration = 1
            last_rework_count = 0
            pm_decision = ""

            for db_step in db_steps:
                # Only include steps that actually completed (have finished_at)
                if db_step.finished_at is None:
                    continue

                # Read artifact YAML from disk
                artifact_yaml = ""
                artifact_type = ""
                for art in db_step.artifacts:
                    artifact_type = art.artifact_type or ""
                    fpath = Path(art.file_path)
                    try:
                        if fpath.is_file():
                            artifact_yaml = fpath.read_text(encoding="utf-8")
                            latest_artifacts[artifact_type] = artifact_yaml
                    except (OSError, UnicodeDecodeError) as exc:
                        logger.warning(
                            "Failed to read artifact file %s for run=%s step=%d: %s",
                            fpath, run_id, db_step.step_num, exc,
                        )
                    break  # one artifact per step

                step_result = StepResult(
                    step_id=f"step_{db_step.step_num}_{db_step.agent_name}",
                    agent_id=db_step.agent_name,
                    artifact_yaml=artifact_yaml,
                    artifact_type=artifact_type,
                    model_used=db_step.model_used or "",
                    validation_result=db_step.verdict,
                    narrative="",  # narrative not persisted to DB
                    reporting_events=[],
                )
                # Optional tracking fields
                step_result["provider"] = db_step.provider or ""
                step_result["input_tokens"] = db_step.input_tokens
                step_result["output_tokens"] = db_step.output_tokens
                step_result["cache_read_tokens"] = db_step.cache_read_tokens
                step_result["cache_creation_tokens"] = db_step.cache_creation_tokens
                step_result["started_at"] = db_step.started_at
                step_result["finished_at"] = db_step.finished_at
                step_result["step_num"] = db_step.step_num
                step_result["iteration_num"] = db_step.iteration_num
                step_result["rework_seq"] = db_step.rework_seq or 0

                steps_completed.append(step_result)
                last_iteration = max(last_iteration, db_step.iteration_num)

                # Track rework state
                if db_step.verdict in ("fail", "warning"):
                    last_rework_count += 1
                elif db_step.verdict == "pass":
                    last_rework_count = 0

            # Determine pm_decision from the last PMAgent step's actual verdict
            for sr in reversed(steps_completed):
                if sr["agent_id"] == "PMAgent":
                    verdict = sr.get("validation_result", "")
                    if verdict in ("stop", "fail"):
                        pm_decision = "stop"
                    else:
                        pm_decision = "continue"
                    break

            # Read max_reworks_per_gate from pipeline definition
            pipeline_path = PIPELINES_DIR / f"{db_run.pipeline_name}.yaml"
            if not pipeline_path.is_file():
                pipeline_path = Path(db_run.pipeline_name)
            try:
                pipeline_def = load_pipeline_definition(pipeline_path)
                max_reworks = pipeline_def.max_reworks_per_gate
            except Exception:
                max_reworks = 3  # fallback default

            state: PipelineState = {
                "user_story": db_run.user_story,
                "steps_completed": steps_completed,
                "latest_artifacts": latest_artifacts,
                "current_step_index": 0,
                "iteration_count": last_iteration,
                "max_iterations": db_run.max_iterations or 3,
                "rework_count": last_rework_count,
                "max_reworks_per_gate": max_reworks,
                "pipeline_status": "running",
                "pm_decision": pm_decision,
            }
            return state

    async def resume_run(self, run_id: str) -> RunRecord:
        """Resume a previously failed/cancelled run from where it stopped.

        Restores PipelineState from DB and re-executes the pipeline graph.
        The graph will replay routing decisions based on restored state,
        effectively skipping already-completed steps.
        """
        loop = asyncio.get_running_loop()

        # Validate the run exists and is in a resumable state
        with self._session_factory() as session:
            db_run = repo.get_run(session, run_id)
            if db_run is None:
                raise ValueError(f"Run '{run_id}' not found")
            if db_run.status not in ("failed", "cancelled"):
                raise ValueError(
                    f"Run '{run_id}' cannot be resumed (status: {db_run.status}). "
                    f"Only 'failed' or 'cancelled' runs can be resumed."
                )
            pipeline_name = db_run.pipeline_name
            max_iterations = db_run.max_iterations or 3

            # Restore webhook settings
            webhook_url = db_run.webhook_url
            webhook_events: list[str] | None = None
            if db_run.webhook_events:
                try:
                    webhook_events = json.loads(db_run.webhook_events)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Reset run status to running
            repo.update_run_status(session, run_id, "running", error=None)

        # Clean up incomplete step rows (started but never finished)
        with self._session_factory() as session:
            repo.delete_incomplete_steps(session, run_id)

        # Restore state
        restored_state = self._restore_pipeline_state(run_id)

        # Pre-seed step counters so new steps get correct sequential numbers
        resume_step_counts: dict[int, int] = {}
        for sr in restored_state["steps_completed"]:
            iter_num = sr.get("iteration_num", 1)
            resume_step_counts[iter_num] = resume_step_counts.get(iter_num, 0) + 1

        on_emit, artifact_saver = self._make_run_callbacks(
            run_id, resume_step_counts=resume_step_counts,
        )

        record = RunRecord(
            run_id=run_id,
            pipeline_name=pipeline_name,
            user_story=restored_state["user_story"],
            max_iterations=max_iterations,
            status=RunStatus.PENDING,
            event_bus=EventBus(loop=loop, on_emit=on_emit),
            current_iteration=restored_state["iteration_count"],
            webhook_url=webhook_url,
            webhook_events=webhook_events,
        )
        record.artifact_saver = artifact_saver
        record.restored_state = restored_state
        self._active_runs[run_id] = record

        asyncio.create_task(self._execute_run(record, is_resume=True))
        return record

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    async def start_run(
        self,
        pipeline_name: str,
        user_story: str,
        max_iterations: int = 3,
        project_id: str | None = None,
        webhook_url: str | None = None,
        webhook_events: list[str] | None = None,
    ) -> RunRecord:
        """Start a pipeline run in the background. Returns immediately."""
        run_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()

        # Normalize webhook_events to JSON string for DB storage
        webhook_events_json: str | None = None
        if webhook_url and webhook_events:
            import json as _json
            webhook_events_json = _json.dumps(webhook_events)

        # Persist to DB
        with self._session_factory() as session:
            repo.create_run(
                session,
                run_id=run_id,
                pipeline_name=pipeline_name,
                user_story=user_story,
                max_iterations=max_iterations,
                project_id=project_id,
                webhook_url=webhook_url,
                webhook_events=webhook_events_json,
            )

        on_emit, artifact_saver = self._make_run_callbacks(run_id)

        record = RunRecord(
            run_id=run_id,
            pipeline_name=pipeline_name,
            user_story=user_story,
            max_iterations=max_iterations,
            status=RunStatus.PENDING,
            event_bus=EventBus(loop=loop, on_emit=on_emit),
            project_id=project_id,
            webhook_url=webhook_url,
            webhook_events=webhook_events,
        )
        record.artifact_saver = artifact_saver
        self._active_runs[run_id] = record

        asyncio.create_task(self._execute_run(record))
        return record

    def _make_run_callbacks(
        self,
        run_id: str,
        *,
        resume_step_counts: dict[int, int] | None = None,
    ):
        """Create on_emit callback and artifact saver sharing step tracking state.

        Args:
            resume_step_counts: Pre-seed iteration→step-count for resume so
                that new steps get the correct sequential step numbers.

        Returns (on_emit, artifact_saver) tuple.
        """
        iterations_created: set[int] = set(resume_step_counts) if resume_step_counts else set()
        step_counter_per_iter: dict[int, int] = dict(resume_step_counts) if resume_step_counts else {}

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

        def _artifact_saver(
            iter_num: int,
            agent_id: str,
            artifact_type: str,
            artifact_yaml: str,
            code_blocks: list[dict[str, str]] | None = None,
        ) -> None:
            """Save artifact YAML to disk and DB immediately after step completion."""
            step_num_in_iter = step_counter_per_iter.get(iter_num, 1)
            try:
                artifact_id = extract_artifact_id(artifact_yaml)
                file_path = self._save_artifact_file(
                    run_id, iter_num, step_num_in_iter, artifact_type, artifact_yaml,
                )
                with self._session_factory() as session:
                    repo.insert_artifact(
                        session,
                        run_id=run_id,
                        iteration_num=iter_num,
                        step_num=step_num_in_iter,
                        agent_name=agent_id,
                        artifact_type=artifact_type,
                        artifact_id=artifact_id,
                        file_path=str(file_path),
                    )

                # Extract code files for ImplementationArtifact
                if artifact_type.startswith("ImplementationArtifact") and code_blocks:
                    workspace_dir = get_runs_dir() / run_id / f"iteration-{iter_num:02d}" / "workspace"
                    written = write_code_blocks(code_blocks, workspace_dir)
                    with self._session_factory() as session:
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
            except Exception:
                logger.exception(
                    "Failed to save artifact for run=%s iter=%d step=%d",
                    run_id, iter_num, step_num_in_iter,
                )
                # Emit SSE warning so frontend can show real-time notification
                record = self._active_runs.get(run_id)
                if record:
                    record.event_bus.emit(RunEvent(
                        event_type=EventType.PIPELINE_WARNING,
                        data={
                            "run_id": run_id,
                            "message": f"Artifact save failed for step {step_num_in_iter} (iter {iter_num})",
                            "agent_id": agent_id,
                            "iteration_num": iter_num,
                        },
                    ))

        return _on_emit, _artifact_saver

    async def _execute_run(self, record: RunRecord, is_resume: bool = False) -> None:
        """Acquire semaphore, run pipeline in thread, emit events, persist results."""
        async with self._semaphore:
            record.status = RunStatus.RUNNING
            if not is_resume:
                with self._session_factory() as session:
                    repo.update_run_status(session, record.run_id, "running")

            mode_label = "resuming" if is_resume else "starting"
            record.event_bus.emit(
                RunEvent(
                    event_type=EventType.PIPELINE_STARTED,
                    data={
                        "run_id": record.run_id,
                        "pipeline": record.pipeline_name,
                        "message": f"Pipeline '{record.pipeline_name}' {mode_label}",
                        "is_resume": is_resume,
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

            artifact_saver = record.artifact_saver
            restored_state = record.restored_state

            def _run_sync() -> dict:
                # Check cancellation before starting
                if record.cancel_event.is_set():
                    raise CancelledError(record.run_id)
                with capture_prints(
                    event_emitter=record.event_bus.emit,
                    cancel_event=record.cancel_event,
                    artifact_saver=artifact_saver,
                ):
                    if is_resume and restored_state is not None:
                        return resume_pipeline(pipeline_def, restored_state)
                    return run_pipeline(pipeline_def, record.user_story)

            try:
                final_state = await asyncio.to_thread(_run_sync)
                record.final_state = dict(final_state)
                record.status = RunStatus.COMPLETED
                record.finished_at = time.time()

                # Finalize DB state (status, iterations, events) before emitting completion
                try:
                    await asyncio.to_thread(self._persist_completed_run, record)
                except Exception as persist_exc:
                    logger.exception(
                        "Post-run persistence failed for run %s (pipeline succeeded)",
                        record.run_id,
                    )
                    # Still mark as completed — pipeline itself succeeded.
                    # Record the persistence error so users can see partial data warning.
                    persist_error = f"Pipeline completed but post-run persistence failed: {persist_exc}"
                    record.error = persist_error[:2000]
                    try:
                        with self._session_factory() as session:
                            repo.update_run_status(
                                session, record.run_id, "completed",
                                finished_at=record.finished_at,
                                error=record.error,
                            )
                    except Exception:
                        logger.exception("Failed to update run status for %s", record.run_id)

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
                self._safe_update_run_status(record.run_id, "cancelled", record.finished_at, record.error)

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
                self._safe_update_run_status(record.run_id, "failed", record.finished_at, record.error)

            except Exception as exc:
                record.status = RunStatus.FAILED
                record.finished_at = time.time()
                error_msg = f"{type(exc).__name__}: {exc}"
                record.error = error_msg[:2000]
                logger.exception("Pipeline run %s failed", record.run_id)
                record.event_bus.emit(
                    RunEvent(
                        event_type=EventType.PIPELINE_ERROR,
                        data={"run_id": record.run_id, "error": record.error},
                    )
                )
                self._safe_update_run_status(record.run_id, "failed", record.finished_at, record.error)

            finally:
                record.event_bus.close()
                record.event_bus.clear()
                # Send webhook notification (fire-and-forget)
                if record.webhook_url:
                    asyncio.create_task(self._send_webhook(record))
                # Clean up active run from memory
                self._active_runs.pop(record.run_id, None)

    def _safe_update_run_status(
        self,
        run_id: str,
        status: str,
        finished_at: float | None = None,
        error: str | None = None,
    ) -> None:
        """Update run status in DB with exception safety."""
        try:
            with self._session_factory() as session:
                repo.update_run_status(session, run_id, status, finished_at=finished_at, error=error)
        except Exception:
            logger.exception("Failed to update run status for %s to '%s'", run_id, status)

    # ------------------------------------------------------------------
    # Post-run persistence (called from thread)
    # ------------------------------------------------------------------

    def _persist_completed_run(self, record: RunRecord) -> None:
        """Finalize a completed run in DB.

        Iterations, steps, artifacts, and code files are already persisted in
        real time via on_emit callback and artifact_saver.
        This method handles: run status update, rework_seq backfill,
        satisfaction scores, iteration finalization, and event log persistence.
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

            # 2) Backfill metadata not available at real-time callback time
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

            # 4) Persist events from EventBus
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
        artifact_dir = get_runs_dir() / run_id / f"iteration-{iteration_num:02d}" / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{step_num:03d}_{artifact_type}.yaml"
        file_path = artifact_dir / filename
        file_path.write_text(yaml_content, encoding="utf-8")
        return file_path

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
                # Use embedded context if available
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

    # ------------------------------------------------------------------
    # Webhook notification
    # ------------------------------------------------------------------

    async def _send_webhook(self, record: RunRecord, max_retries: int = 3) -> None:
        """Send webhook notification for a completed/failed/cancelled run.

        Retries up to max_retries times with exponential backoff.
        Failures are logged but never affect run state.
        """
        if not record.webhook_url:
            return

        # Check if this status is in the subscribed event list
        status_value = record.status.value  # completed, failed, cancelled
        if record.webhook_events and status_value not in record.webhook_events:
            return

        total_tokens = 0
        iterations_completed = 0
        if record.final_state:
            for sr in record.final_state.get("steps_completed", []):
                total_tokens += (sr.get("input_tokens") or 0) + (sr.get("output_tokens") or 0)
            iterations_completed = record.final_state.get("iteration_count", 0)

        elapsed = round(record.finished_at - record.created_at, 1) if record.finished_at else None

        payload = {
            "run_id": record.run_id,
            "status": status_value,
            "pipeline_name": record.pipeline_name,
            "project_id": record.project_id,
            "iterations_completed": iterations_completed,
            "total_tokens": total_tokens,
            "elapsed_seconds": elapsed,
            "error": record.error,
            "artifacts_url": f"/api/runs/{record.run_id}/artifacts",
        }

        import httpx

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(record.webhook_url, json=payload)
                    if resp.status_code < 400:
                        logger.info(
                            "Webhook sent for run %s → %s (status %d)",
                            record.run_id, record.webhook_url, resp.status_code,
                        )
                        return
                    logger.warning(
                        "Webhook returned %d for run %s (attempt %d/%d)",
                        resp.status_code, record.run_id, attempt + 1, max_retries,
                    )
            except Exception as exc:
                logger.warning(
                    "Webhook failed for run %s (attempt %d/%d): %s",
                    record.run_id, attempt + 1, max_retries, exc,
                )

            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 1s, 2s backoff

        logger.error(
            "Webhook exhausted retries for run %s → %s",
            record.run_id, record.webhook_url,
        )
