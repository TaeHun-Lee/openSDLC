"""Pipeline run endpoints — start, status, events (SSE), artifacts, progress, cancel."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.artifacts.code_extractor import extract_code_files, get_runtime_info
from app.core.artifacts.parser import extract_artifact_id
from app.db import repository as repo
from app.models.requests import StartRunRequest
from app.models.responses import (
    ArtifactInfo,
    ArtifactRef,
    CodeFileInfo,
    CodeFileRef,
    EventInfo,
    IterationInfo,
    ProgressInfo,
    RunArtifacts,
    RunCreated,
    RunDetail,
    RunSummary,
    StepDetailInfo,
    StepResultInfo,
)
from app.services.run_manager import RunManager

router = APIRouter(prefix="/runs", tags=["runs"])


def _get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager


def _get_session_factory(request: Request):
    return request.app.state.session_factory


# ------------------------------------------------------------------
# Start run
# ------------------------------------------------------------------

@router.post("", response_model=RunCreated, status_code=201)
async def start_run(body: StartRunRequest, request: Request) -> RunCreated:
    """Start a new pipeline run. Returns immediately with run_id."""
    manager = _get_run_manager(request)
    record = await manager.start_run(
        pipeline_name=body.pipeline,
        user_story=body.user_story,
        max_iterations=body.max_iterations,
        project_id=body.project_id,
    )
    return RunCreated(
        run_id=record.run_id,
        status=record.status.value,
        pipeline=record.pipeline_name,
    )


# ------------------------------------------------------------------
# List runs
# ------------------------------------------------------------------

@router.get("", response_model=list[RunSummary])
def list_runs(request: Request, project_id: str | None = None) -> list[RunSummary]:
    """List all pipeline runs (optionally filtered by project)."""
    sf = _get_session_factory(request)
    with sf() as session:
        db_runs = repo.list_runs(session, project_id=project_id)
        return [
            RunSummary(
                run_id=r.run_id,
                pipeline_name=r.pipeline_name,
                status=r.status,
                created_at=r.created_at,
                finished_at=r.finished_at,
                error=r.error,
            )
            for r in db_runs
        ]


# ------------------------------------------------------------------
# Get run detail
# ------------------------------------------------------------------

@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: str, request: Request) -> RunDetail:
    """Get detailed run status including iterations, steps, and artifacts."""
    manager = _get_run_manager(request)
    sf = _get_session_factory(request)

    # Check active in-memory run first (has real-time state)
    active = manager.get_run(run_id)

    with sf() as session:
        db_run = repo.get_run(session, run_id)
        if db_run is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

        # Build iteration tree from DB
        iterations_info: list[IterationInfo] = []
        db_iterations = repo.get_iterations(session, run_id)
        for db_iter in db_iterations:
            steps_info = [
                StepDetailInfo(
                    step_num=s.step_num,
                    agent_name=s.agent_name,
                    mode=s.mode,
                    verdict=s.verdict,
                    model_used=s.model_used,
                    provider=s.provider,
                    input_tokens=s.input_tokens,
                    output_tokens=s.output_tokens,
                    cache_read_tokens=s.cache_read_tokens,
                    cache_creation_tokens=s.cache_creation_tokens,
                    rework_seq=s.rework_seq or 0,
                    started_at=s.started_at,
                    finished_at=s.finished_at,
                    artifacts=[
                        ArtifactRef(
                            artifact_type=a.artifact_type,
                            artifact_id=a.artifact_id,
                            file_path=a.file_path,
                        )
                        for a in s.artifacts
                    ],
                )
                for s in db_iter.steps
            ]
            code_refs = [
                CodeFileRef(
                    relative_path=cf.relative_path,
                    file_path=cf.file_path,
                    size_bytes=cf.size_bytes,
                )
                for cf in db_iter.code_files
            ]
            iterations_info.append(IterationInfo(
                iteration_num=db_iter.iteration_num,
                status=db_iter.status or "running",
                satisfaction_score=db_iter.satisfaction_score,
                started_at=db_iter.started_at,
                finished_at=db_iter.finished_at,
                steps=steps_info,
                code_files=code_refs,
            ))

        # Legacy flat steps + artifacts from active in-memory state
        flat_steps: list[StepResultInfo] = []
        flat_artifacts: dict[str, str] = {}
        if active and active.final_state:
            for sr in active.final_state.get("steps_completed", []):
                flat_steps.append(
                    StepResultInfo(
                        step_id=sr["step_id"],
                        agent_id=sr["agent_id"],
                        artifact_type=sr["artifact_type"],
                        model_used=sr["model_used"],
                        validation_result=sr.get("validation_result"),
                        narrative=sr.get("narrative", ""),
                    )
                )
            flat_artifacts = active.final_state.get("latest_artifacts", {})

        return RunDetail(
            run_id=db_run.run_id,
            pipeline_name=db_run.pipeline_name,
            user_story=db_run.user_story,
            status=active.status.value if active else db_run.status,
            max_iterations=db_run.max_iterations or 3,
            project_id=db_run.project_id,
            created_at=db_run.created_at,
            finished_at=db_run.finished_at,
            iterations=iterations_info,
            steps=flat_steps,
            artifacts=flat_artifacts,
            error=db_run.error,
        )


# ------------------------------------------------------------------
# SSE events (real-time for active runs, DB replay for completed)
# ------------------------------------------------------------------

@router.get("/{run_id}/events")
async def stream_events(
    run_id: str,
    request: Request,
    last_event_id: int = 0,
    iteration_num: int | None = None,
    agent_name: str | None = None,
):
    """SSE stream of real-time pipeline events.

    For active runs: live stream from EventBus.
    For completed runs: replay from DB (filterable by iteration_num, agent_name).
    """
    manager = _get_run_manager(request)
    active = manager.get_run(run_id)

    if active is not None:
        # Live SSE stream with disconnect detection
        async def event_generator():
            async for idx, event in active.event_bus.subscribe(last_index=last_event_id):
                if await request.is_disconnected():
                    break
                yield event.to_sse(event_id=idx)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Replay from DB for completed runs
    sf = _get_session_factory(request)
    with sf() as session:
        db_run = repo.get_run(session, run_id)
        if db_run is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

        db_events = repo.list_events(
            session, run_id,
            iteration_num=iteration_num,
            agent_name=agent_name,
        )

    return [
        EventInfo(
            id=e.id,
            event_type=e.event_type,
            agent_name=e.agent_name,
            message=e.message,
            iteration_num=e.iteration_num,
            created_at=e.created_at,
        )
        for e in db_events
    ]


# ------------------------------------------------------------------
# Artifacts
# ------------------------------------------------------------------

@router.get("/{run_id}/artifacts", response_model=RunArtifacts)
def get_artifacts(run_id: str, request: Request, iteration_num: int | None = None) -> RunArtifacts:
    """Get all artifacts from a run (optionally filtered by iteration)."""
    manager = _get_run_manager(request)
    sf = _get_session_factory(request)

    artifact_list: list[ArtifactInfo] = []
    code_files_list: list[CodeFileInfo] = []
    runtime_info: dict[str, str] = {}

    # Try DB first (completed runs have artifacts on disk)
    with sf() as session:
        db_artifacts = repo.list_artifacts(session, run_id, iteration_num=iteration_num)
        for a in db_artifacts:
            fpath = Path(a.file_path)
            if fpath.is_file():
                yaml_content = fpath.read_text(encoding="utf-8")
                artifact_list.append(ArtifactInfo(
                    artifact_type=a.artifact_type or "",
                    artifact_id=a.artifact_id,
                    yaml_content=yaml_content,
                ))

        db_code_files = repo.list_code_files(session, run_id, iteration_num=iteration_num)
        for cf in db_code_files:
            fpath = Path(cf.file_path)
            if fpath.is_file():
                content = fpath.read_text(encoding="utf-8")
                lang = _guess_language(cf.relative_path)
                code_files_list.append(CodeFileInfo(
                    path=cf.relative_path,
                    language=lang,
                    content=content,
                ))

    # Fallback: if DB has no artifacts (still running), use in-memory state
    if not artifact_list:
        active = manager.get_run(run_id)
        if active and active.final_state:
            latest = active.final_state.get("latest_artifacts", {})
            for atype, yaml_content in latest.items():
                if yaml_content:
                    artifact_list.append(ArtifactInfo(
                        artifact_type=atype,
                        artifact_id=extract_artifact_id(yaml_content),
                        yaml_content=yaml_content,
                    ))
            impl_yaml = latest.get("ImplementationArtifact", "")
            if impl_yaml:
                for cf in extract_code_files(impl_yaml):
                    code_files_list.append(CodeFileInfo(
                        path=cf["path"],
                        language=cf.get("language", ""),
                        content=cf["content"],
                    ))
                runtime_info = get_runtime_info(impl_yaml)

    return RunArtifacts(
        run_id=run_id,
        artifacts=artifact_list,
        code_files=code_files_list,
        runtime_info=runtime_info,
    )


# ------------------------------------------------------------------
# Progress snapshot (polling alternative to SSE)
# ------------------------------------------------------------------

@router.get("/{run_id}/progress", response_model=ProgressInfo)
def get_progress(run_id: str, request: Request) -> ProgressInfo:
    """Get real-time progress snapshot for a running pipeline.

    Returns current iteration, step, agent, and elapsed time.
    For completed/failed runs, returns final status from DB.
    """
    manager = _get_run_manager(request)
    active = manager.get_run(run_id)

    if active is not None:
        elapsed = time.time() - active.created_at
        return ProgressInfo(
            run_id=run_id,
            status=active.status.value,
            current_iteration=active.current_iteration,
            current_step=active.current_step,
            current_agent=active.current_agent,
            steps_total=active.steps_total,
            elapsed_seconds=round(elapsed, 1),
        )

    # Fallback to DB for completed runs
    sf = _get_session_factory(request)
    with sf() as session:
        db_run = repo.get_run(session, run_id)
        if db_run is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        elapsed = None
        if db_run.finished_at and db_run.created_at:
            elapsed = round(db_run.finished_at - db_run.created_at, 1)
        return ProgressInfo(
            run_id=run_id,
            status=db_run.status,
            elapsed_seconds=elapsed,
        )


# ------------------------------------------------------------------
# Cancel run
# ------------------------------------------------------------------

@router.post("/{run_id}/cancel", status_code=202)
def cancel_run(run_id: str, request: Request) -> dict:
    """Request cancellation of a running pipeline.

    The pipeline will stop after the current step completes.
    """
    manager = _get_run_manager(request)
    if not manager.cancel_run(run_id):
        sf = _get_session_factory(request)
        with sf() as session:
            db_run = repo.get_run(session, run_id)
            if db_run is None:
                raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
            raise HTTPException(
                status_code=409,
                detail=f"Run '{run_id}' is not active (status: {db_run.status})",
            )
    return {"run_id": run_id, "message": "Cancellation requested"}


def _guess_language(filename: str) -> str:
    """Guess programming language from file extension."""
    ext_map = {
        ".html": "html", ".css": "css", ".js": "javascript", ".ts": "typescript",
        ".py": "python", ".java": "java", ".go": "go", ".rs": "rust",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".md": "markdown",
    }
    for ext, lang in ext_map.items():
        if filename.endswith(ext):
            return lang
    return ""
