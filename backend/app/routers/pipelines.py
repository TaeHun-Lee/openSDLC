"""Pipeline CRUD endpoints."""

from __future__ import annotations

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.core.config import PIPELINES_DIR
from app.core.pipeline.graph_builder import load_pipeline_definition
from app.models.requests import CreatePipelineRequest, UpdatePipelineRequest
from app.models.responses import PipelineInfo, PipelineListItem, PipelineValidationResult, StepInfo
from app.services.pipeline_compiler import (
    compile_pipeline,
    load_and_merge_update,
    save_pipeline_yaml,
    validate_pipeline_request,
    validate_pipeline_runtime,
)

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

DEFAULT_PIPELINE = "full_spiral"


def _is_default(name: str) -> bool:
    return name == DEFAULT_PIPELINE


def _to_pipeline_info(path, *, is_default: bool) -> PipelineInfo:
    pipeline_def = load_pipeline_definition(path)
    return PipelineInfo(
        name=pipeline_def.name,
        description=pipeline_def.description,
        max_iterations=pipeline_def.max_iterations,
        max_reworks_per_gate=pipeline_def.max_reworks_per_gate,
        steps=[
            StepInfo(
                step=s.step,
                agent=s.agent,
                model=s.model,
                provider=s.provider,
                on_fail=s.on_fail,
                mode=s.mode,
            )
            for s in pipeline_def.steps
        ],
        is_default=is_default,
    )


# --- READ ---


@router.get("", response_model=list[PipelineListItem])
async def list_pipelines() -> list[PipelineListItem]:
    """List all available pipeline definitions."""
    items: list[PipelineListItem] = []
    if not PIPELINES_DIR.is_dir():
        return items

    for path in sorted(PIPELINES_DIR.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            items.append(
                PipelineListItem(
                    name=path.stem,
                    description=raw.get("description", ""),
                    step_count=len(raw.get("steps", [])),
                    is_default=_is_default(path.stem),
                )
            )
        except Exception:
            continue

    return items


@router.get("/{name}", response_model=PipelineInfo)
async def get_pipeline(name: str) -> PipelineInfo:
    """Get detailed pipeline definition by name."""
    path = PIPELINES_DIR / f"{name}.yaml"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Pipeline '{name}' not found")

    return _to_pipeline_info(path, is_default=_is_default(name))


# --- VALIDATE ---


@router.post("/{name}/validate", response_model=PipelineValidationResult)
async def validate_pipeline(name: str) -> PipelineValidationResult:
    """Validate a pipeline definition against the runtime environment.

    Checks agent existence, API key availability, artifact input/output
    compatibility, rework routing reachability, and iteration routing.
    """
    path = PIPELINES_DIR / f"{name}.yaml"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Pipeline '{name}' not found")

    pipeline_def = load_pipeline_definition(path)
    return validate_pipeline_runtime(pipeline_def)


# --- CREATE ---


@router.post("", response_model=PipelineInfo, status_code=201)
async def create_pipeline(body: CreatePipelineRequest) -> PipelineInfo:
    """Create a new pipeline definition."""
    path = PIPELINES_DIR / f"{body.name}.yaml"
    if path.is_file():
        raise HTTPException(
            status_code=409,
            detail=f"Pipeline '{body.name}' already exists. Use PUT to update.",
        )

    errors = validate_pipeline_request(body.steps)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    pipeline_def = compile_pipeline(body)
    save_pipeline_yaml(path, pipeline_def)

    return _to_pipeline_info(path, is_default=False)


# --- UPDATE ---


@router.put("/{name}", response_model=PipelineInfo)
async def update_pipeline(name: str, body: UpdatePipelineRequest) -> PipelineInfo:
    """Update an existing pipeline definition. Default pipeline cannot be modified."""
    if _is_default(name):
        raise HTTPException(
            status_code=403,
            detail=f"Default pipeline '{name}' cannot be modified.",
        )

    path = PIPELINES_DIR / f"{name}.yaml"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Pipeline '{name}' not found")

    merged_request = load_and_merge_update(
        existing_path=path,
        description=body.description,
        max_iterations=body.max_iterations,
        max_reworks_per_gate=body.max_reworks_per_gate,
        steps=body.steps,
    )

    errors = validate_pipeline_request(merged_request.steps)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    pipeline_def = compile_pipeline(merged_request)
    save_pipeline_yaml(path, pipeline_def)

    return _to_pipeline_info(path, is_default=False)


# --- DELETE ---


@router.delete("/{name}", status_code=204)
async def delete_pipeline(name: str) -> Response:
    """Delete a pipeline definition. Default pipeline cannot be deleted."""
    if _is_default(name):
        raise HTTPException(
            status_code=403,
            detail=f"Default pipeline '{name}' cannot be deleted.",
        )

    path = PIPELINES_DIR / f"{name}.yaml"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Pipeline '{name}' not found")

    path.unlink()
    return Response(status_code=204)
