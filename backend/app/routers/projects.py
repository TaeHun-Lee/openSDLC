"""Project CRUD endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from sqlalchemy import func, select

from app.db import repository as repo
from app.db.models import Run
from app.models.requests import CreateProjectRequest, UpdateProjectRequest
from app.models.responses import (
    ModelUsage,
    PipelineUsage,
    ProjectDetail,
    ProjectInfo,
    ProjectUsage,
    RunSummary,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _sf(request: Request):
    return request.app.state.session_factory


@router.post("", response_model=ProjectInfo, status_code=201)
def create_project(body: CreateProjectRequest, request: Request) -> ProjectInfo:
    """Create a new project."""
    sf = _sf(request)
    project_id = str(uuid.uuid4())
    with sf() as session:
        proj = repo.create_project(
            session,
            project_id=project_id,
            name=body.name,
            description=body.description,
        )
        return ProjectInfo(
            project_id=proj.project_id,
            name=proj.name,
            description=proj.description or "",
            created_at=proj.created_at,
            run_count=0,  # just created, no runs yet
        )


@router.get("", response_model=list[ProjectInfo])
def list_projects(request: Request) -> list[ProjectInfo]:
    """List all projects."""
    sf = _sf(request)
    with sf() as session:
        projects = repo.list_projects(session)
        # Efficient count query instead of loading all runs per project
        project_ids = [p.project_id for p in projects]
        run_counts: dict[str, int] = {}
        if project_ids:
            stmt = (
                select(Run.project_id, func.count().label("cnt"))
                .where(Run.project_id.in_(project_ids))
                .group_by(Run.project_id)
            )
            run_counts = {row.project_id: row.cnt for row in session.execute(stmt).all()}
        return [
            ProjectInfo(
                project_id=p.project_id,
                name=p.name,
                description=p.description or "",
                created_at=p.created_at,
                run_count=run_counts.get(p.project_id, 0),
            )
            for p in projects
        ]


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, request: Request) -> ProjectDetail:
    """Get project detail including its runs (user stories)."""
    sf = _sf(request)
    with sf() as session:
        proj = repo.get_project(session, project_id)
        if proj is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        runs = repo.list_runs(session, project_id=project_id)
        return ProjectDetail(
            project_id=proj.project_id,
            name=proj.name,
            description=proj.description or "",
            created_at=proj.created_at,
            runs=[
                RunSummary(
                    run_id=r.run_id,
                    pipeline_name=r.pipeline_name,
                    status=r.status,
                    created_at=r.created_at,
                    finished_at=r.finished_at,
                    error=r.error,
                )
                for r in runs
            ],
        )


@router.put("/{project_id}", response_model=ProjectInfo)
def update_project(project_id: str, body: UpdateProjectRequest, request: Request) -> ProjectInfo:
    """Update project name and/or description."""
    sf = _sf(request)
    with sf() as session:
        proj = repo.update_project(
            session,
            project_id=project_id,
            name=body.name,
            description=body.description,
        )
        if proj is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        run_count = session.scalar(
            select(func.count()).select_from(Run).where(Run.project_id == project_id)
        ) or 0
        return ProjectInfo(
            project_id=proj.project_id,
            name=proj.name,
            description=proj.description or "",
            created_at=proj.created_at,
            run_count=run_count,
        )


@router.get("/{project_id}/usage", response_model=ProjectUsage)
def get_project_usage(project_id: str, request: Request) -> ProjectUsage:
    """Aggregate token usage across all runs in a project."""
    sf = _sf(request)
    with sf() as session:
        proj = repo.get_project(session, project_id)
        if proj is None:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        raw = repo.get_project_usage(session, project_id)
        return ProjectUsage(
            project_id=project_id,
            total_runs=raw["total_runs"],
            total_input_tokens=raw["total_input_tokens"],
            total_output_tokens=raw["total_output_tokens"],
            total_cache_read_tokens=raw["total_cache_read_tokens"],
            total_cache_creation_tokens=raw["total_cache_creation_tokens"],
            by_model={k: ModelUsage(**v) for k, v in raw["by_model"].items()},
            by_pipeline={k: PipelineUsage(**v) for k, v in raw["by_pipeline"].items()},
        )


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, request: Request) -> Response:
    """Delete a project. Runs under this project will have project_id set to NULL."""
    sf = _sf(request)
    with sf() as session:
        deleted = repo.delete_project(session, project_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return Response(status_code=204)
