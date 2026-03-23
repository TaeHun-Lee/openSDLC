"""Pipeline run endpoints — start, status, events (SSE), artifacts."""

from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.artifacts.parser import extract_artifact_id
from app.core.artifacts.code_extractor import extract_code_files, get_runtime_info
from app.models.requests import StartRunRequest
from app.models.responses import (
    ArtifactInfo,
    CodeFileInfo,
    RunArtifacts,
    RunCreated,
    RunDetail,
    RunSummary,
    StepResultInfo,
)
from app.services.run_manager import RunManager

router = APIRouter(prefix="/runs", tags=["runs"])


def _get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager


@router.post("", response_model=RunCreated, status_code=201)
async def start_run(body: StartRunRequest, request: Request) -> RunCreated:
    """Start a new pipeline run. Returns immediately with run_id."""
    manager = _get_run_manager(request)
    record = await manager.start_run(
        pipeline_name=body.pipeline,
        user_story=body.user_story,
        max_iterations=body.max_iterations,
    )
    return RunCreated(
        run_id=record.run_id,
        status=record.status.value,
        pipeline=record.pipeline_name,
    )


@router.get("", response_model=list[RunSummary])
async def list_runs(request: Request) -> list[RunSummary]:
    """List all pipeline runs."""
    manager = _get_run_manager(request)
    return [
        RunSummary(
            run_id=r.run_id,
            pipeline_name=r.pipeline_name,
            status=r.status.value,
            created_at=r.created_at,
            finished_at=r.finished_at,
            steps_completed=len(r.final_state.get("steps_completed", []))
            if r.final_state
            else 0,
            error=r.error,
        )
        for r in manager.list_runs()
    ]


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(run_id: str, request: Request) -> RunDetail:
    """Get detailed run status including step results."""
    manager = _get_run_manager(request)
    record = manager.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    steps: list[StepResultInfo] = []
    artifacts: dict[str, str] = {}

    if record.final_state:
        for sr in record.final_state.get("steps_completed", []):
            steps.append(
                StepResultInfo(
                    step_id=sr["step_id"],
                    agent_id=sr["agent_id"],
                    artifact_type=sr["artifact_type"],
                    model_used=sr["model_used"],
                    validation_result=sr.get("validation_result"),
                    narrative=sr.get("narrative", ""),
                )
            )
        artifacts = record.final_state.get("latest_artifacts", {})

    return RunDetail(
        run_id=record.run_id,
        pipeline_name=record.pipeline_name,
        user_story=record.user_story,
        status=record.status.value,
        max_iterations=record.max_iterations,
        created_at=record.created_at,
        finished_at=record.finished_at,
        steps=steps,
        artifacts=artifacts,
        error=record.error,
    )


@router.get("/{run_id}/events")
async def stream_events(run_id: str, request: Request, last_event_id: int = 0):
    """SSE stream of real-time pipeline events.

    Query param `last_event_id` supports reconnection — client sends last
    received event ID and gets only new events.
    """
    manager = _get_run_manager(request)
    record = manager.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    async def event_generator():
        async for idx, event in record.event_bus.subscribe(last_index=last_event_id):
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


@router.get("/{run_id}/artifacts", response_model=RunArtifacts)
async def get_artifacts(run_id: str, request: Request) -> RunArtifacts:
    """Get all artifacts from a completed (or in-progress) run."""
    manager = _get_run_manager(request)
    record = manager.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    artifact_list: list[ArtifactInfo] = []
    code_files_list: list[CodeFileInfo] = []
    runtime_info: dict[str, str] = {}

    if record.final_state:
        latest = record.final_state.get("latest_artifacts", {})
        for atype, yaml_content in latest.items():
            if yaml_content:
                artifact_list.append(
                    ArtifactInfo(
                        artifact_type=atype,
                        artifact_id=extract_artifact_id(yaml_content),
                        yaml_content=yaml_content,
                    )
                )

        # Extract code files from ImplementationArtifact
        impl_yaml = latest.get("ImplementationArtifact", "")
        if impl_yaml:
            for cf in extract_code_files(impl_yaml):
                code_files_list.append(
                    CodeFileInfo(
                        path=cf["path"],
                        language=cf.get("language", ""),
                        content=cf["content"],
                    )
                )
            runtime_info = get_runtime_info(impl_yaml)

    return RunArtifacts(
        run_id=run_id,
        artifacts=artifact_list,
        code_files=code_files_list,
        runtime_info=runtime_info,
    )
