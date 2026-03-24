"""Database CRUD operations for all OpenSDLC entities.

All functions take an explicit Session and commit within the function.
Callers use `with session_factory() as session:` blocks.
"""

from __future__ import annotations

import time
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Artifact,
    CodeFile,
    Event,
    Iteration,
    Project,
    Run,
    Step,
)


# ======================================================================
# Project
# ======================================================================


def create_project(
    session: Session,
    project_id: str,
    name: str,
    description: str = "",
) -> Project:
    proj = Project(
        project_id=project_id,
        name=name,
        description=description,
        created_at=time.time(),
        updated_at=time.time(),
    )
    session.add(proj)
    session.commit()
    return proj


def get_project(session: Session, project_id: str) -> Project | None:
    return session.get(Project, project_id)


def list_projects(session: Session) -> Sequence[Project]:
    stmt = select(Project).order_by(Project.created_at.desc())
    return session.scalars(stmt).all()


def update_project(
    session: Session,
    project_id: str,
    name: str | None = None,
    description: str | None = None,
) -> Project | None:
    proj = session.get(Project, project_id)
    if proj is None:
        return None
    if name is not None:
        proj.name = name
    if description is not None:
        proj.description = description
    proj.updated_at = time.time()
    session.commit()
    return proj


def delete_project(session: Session, project_id: str) -> bool:
    proj = session.get(Project, project_id)
    if proj is None:
        return False
    session.delete(proj)
    session.commit()
    return True


# ======================================================================
# Run (= User Story execution)
# ======================================================================


def create_run(
    session: Session,
    run_id: str,
    pipeline_name: str,
    user_story: str,
    max_iterations: int = 3,
    project_id: str | None = None,
) -> Run:
    run = Run(
        run_id=run_id,
        project_id=project_id,
        pipeline_name=pipeline_name,
        user_story=user_story,
        status="pending",
        max_iterations=max_iterations,
        created_at=time.time(),
    )
    session.add(run)
    session.commit()
    return run


def get_run(session: Session, run_id: str) -> Run | None:
    return session.get(Run, run_id)


def list_runs(
    session: Session,
    project_id: str | None = None,
) -> Sequence[Run]:
    stmt = select(Run).order_by(Run.created_at.desc())
    if project_id is not None:
        stmt = stmt.where(Run.project_id == project_id)
    return session.scalars(stmt).all()


def update_run_status(
    session: Session,
    run_id: str,
    status: str,
    finished_at: float | None = None,
    error: str | None = None,
) -> None:
    run = session.get(Run, run_id)
    if run is None:
        return
    run.status = status
    if finished_at is not None:
        run.finished_at = finished_at
    if error is not None:
        run.error = error
    session.commit()


# ======================================================================
# Iteration
# ======================================================================


def create_iteration(
    session: Session,
    run_id: str,
    iteration_num: int,
    started_at: float | None = None,
) -> Iteration:
    iteration = Iteration(
        run_id=run_id,
        iteration_num=iteration_num,
        status="running",
        started_at=started_at or time.time(),
    )
    session.add(iteration)
    session.commit()
    return iteration


def get_iterations(session: Session, run_id: str) -> Sequence[Iteration]:
    """Get all iterations for a run with eager-loaded steps, artifacts, and code_files."""
    stmt = (
        select(Iteration)
        .where(Iteration.run_id == run_id)
        .options(
            joinedload(Iteration.steps).joinedload(Step.artifacts),
            joinedload(Iteration.code_files),
        )
        .order_by(Iteration.iteration_num)
    )
    return session.scalars(stmt).unique().all()


def update_iteration(
    session: Session,
    run_id: str,
    iteration_num: int,
    status: str | None = None,
    satisfaction_score: int | None = None,
    finished_at: float | None = None,
) -> None:
    stmt = (
        select(Iteration)
        .where(Iteration.run_id == run_id, Iteration.iteration_num == iteration_num)
    )
    iteration = session.scalars(stmt).first()
    if iteration is None:
        return
    if status is not None:
        iteration.status = status
    if satisfaction_score is not None:
        iteration.satisfaction_score = satisfaction_score
    if finished_at is not None:
        iteration.finished_at = finished_at
    session.commit()


# ======================================================================
# Step
# ======================================================================


def create_step(
    session: Session,
    run_id: str,
    iteration_num: int,
    step_num: int,
    agent_name: str,
    mode: str | None = None,
    rework_seq: int = 0,
    started_at: float | None = None,
) -> Step:
    step = Step(
        run_id=run_id,
        iteration_num=iteration_num,
        step_num=step_num,
        agent_name=agent_name,
        mode=mode,
        rework_seq=rework_seq,
        started_at=started_at,
    )
    session.add(step)
    session.commit()
    return step


def update_step(
    session: Session,
    run_id: str,
    iteration_num: int,
    step_num: int,
    verdict: str | None = None,
    model_used: str | None = None,
    provider: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cache_read_tokens: int | None = None,
    cache_creation_tokens: int | None = None,
    finished_at: float | None = None,
    rework_seq: int | None = None,
) -> None:
    stmt = select(Step).where(
        Step.run_id == run_id,
        Step.iteration_num == iteration_num,
        Step.step_num == step_num,
    )
    step = session.scalars(stmt).first()
    if step is None:
        return
    if verdict is not None:
        step.verdict = verdict
    if model_used is not None:
        step.model_used = model_used
    if provider is not None:
        step.provider = provider
    if input_tokens is not None:
        step.input_tokens = input_tokens
    if output_tokens is not None:
        step.output_tokens = output_tokens
    if cache_read_tokens is not None:
        step.cache_read_tokens = cache_read_tokens
    if cache_creation_tokens is not None:
        step.cache_creation_tokens = cache_creation_tokens
    if finished_at is not None:
        step.finished_at = finished_at
    if rework_seq is not None:
        step.rework_seq = rework_seq
    session.commit()


# ======================================================================
# Artifact
# ======================================================================


def insert_artifact(
    session: Session,
    run_id: str,
    iteration_num: int,
    step_num: int,
    agent_name: str,
    artifact_type: str,
    artifact_id: str | None,
    file_path: str,
) -> Artifact:
    artifact = Artifact(
        run_id=run_id,
        iteration_num=iteration_num,
        step_num=step_num,
        agent_name=agent_name,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        file_path=file_path,
        created_at=time.time(),
    )
    session.add(artifact)
    session.commit()
    return artifact


def list_artifacts(
    session: Session,
    run_id: str,
    iteration_num: int | None = None,
) -> Sequence[Artifact]:
    stmt = select(Artifact).where(Artifact.run_id == run_id)
    if iteration_num is not None:
        stmt = stmt.where(Artifact.iteration_num == iteration_num)
    stmt = stmt.order_by(Artifact.iteration_num, Artifact.step_num)
    return session.scalars(stmt).all()


# ======================================================================
# CodeFile
# ======================================================================


def insert_code_file(
    session: Session,
    run_id: str,
    iteration_num: int,
    relative_path: str,
    file_path: str,
    size_bytes: int | None = None,
) -> CodeFile:
    cf = CodeFile(
        run_id=run_id,
        iteration_num=iteration_num,
        relative_path=relative_path,
        file_path=file_path,
        size_bytes=size_bytes,
        created_at=time.time(),
    )
    session.add(cf)
    session.commit()
    return cf


def list_code_files(
    session: Session,
    run_id: str,
    iteration_num: int | None = None,
) -> Sequence[CodeFile]:
    stmt = select(CodeFile).where(CodeFile.run_id == run_id)
    if iteration_num is not None:
        stmt = stmt.where(CodeFile.iteration_num == iteration_num)
    stmt = stmt.order_by(CodeFile.iteration_num, CodeFile.relative_path)
    return session.scalars(stmt).all()


# ======================================================================
# Event
# ======================================================================


def bulk_insert_events(session: Session, events: list[Event]) -> None:
    session.add_all(events)
    session.commit()


def list_events(
    session: Session,
    run_id: str,
    iteration_num: int | None = None,
    agent_name: str | None = None,
) -> Sequence[Event]:
    stmt = select(Event).where(Event.run_id == run_id)
    if iteration_num is not None:
        stmt = stmt.where(Event.iteration_num == iteration_num)
    if agent_name is not None:
        stmt = stmt.where(Event.agent_name == agent_name)
    stmt = stmt.order_by(Event.id)
    return session.scalars(stmt).all()
