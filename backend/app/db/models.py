"""SQLAlchemy ORM models for OpenSDLC persistence.

Hierarchy: Project → Run (UserStory) → Iteration → Step → Artifact
                                                  ↘ CodeFile
                                       ↘ Event
"""

from __future__ import annotations

import time

from sqlalchemy import (
    Column,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time, onupdate=time.time)

    runs = relationship("Run", back_populates="project", order_by="Run.created_at.desc()")


class Run(Base):
    """A single pipeline execution — corresponds to one user story."""

    __tablename__ = "runs"

    run_id = Column(String, primary_key=True)
    project_id = Column(String, nullable=True)
    pipeline_name = Column(String, nullable=False)
    user_story = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending|running|completed|failed
    max_iterations = Column(Integer, default=3)
    created_at = Column(Float, default=time.time)
    finished_at = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    workspace_path = Column(Text, nullable=True)
    webhook_url = Column(Text, nullable=True)
    webhook_events = Column(Text, nullable=True)  # JSON list, e.g. '["completed","failed"]'

    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id"], ["projects.project_id"],
            ondelete="SET NULL",
        ),
        Index("ix_runs_project_id", "project_id"),
        Index("ix_runs_status", "status"),
    )

    project = relationship("Project", back_populates="runs")
    iterations = relationship(
        "Iteration", back_populates="run",
        order_by="Iteration.iteration_num",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "Event", back_populates="run",
        order_by="Event.id",
        cascade="all, delete-orphan",
    )


class Iteration(Base):
    __tablename__ = "iterations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    iteration_num = Column(Integer, nullable=False)
    status = Column(String(20), default="running")
    satisfaction_score = Column(Integer, nullable=True)
    started_at = Column(Float, nullable=True)
    finished_at = Column(Float, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["runs.run_id"], ondelete="CASCADE"),
        UniqueConstraint("run_id", "iteration_num"),
    )

    run = relationship("Run", back_populates="iterations")
    steps = relationship(
        "Step", back_populates="iteration",
        order_by="Step.step_num",
        cascade="all, delete-orphan",
    )
    code_files = relationship(
        "CodeFile", back_populates="iteration",
        cascade="all, delete-orphan",
    )


class Step(Base):
    __tablename__ = "steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    iteration_num = Column(Integer, nullable=False)
    step_num = Column(Integer, nullable=False)
    agent_name = Column(String, nullable=False)
    mode = Column(String, nullable=True)
    verdict = Column(String, nullable=True)  # pass|warning|fail
    model_used = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cache_read_tokens = Column(Integer, nullable=True)
    cache_creation_tokens = Column(Integer, nullable=True)
    rework_seq = Column(Integer, default=0)
    started_at = Column(Float, nullable=True)
    finished_at = Column(Float, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "iteration_num"],
            ["iterations.run_id", "iterations.iteration_num"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("run_id", "iteration_num", "step_num"),
    )

    iteration = relationship("Iteration", back_populates="steps")
    artifacts = relationship(
        "Artifact", back_populates="step",
        cascade="all, delete-orphan",
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    iteration_num = Column(Integer, nullable=False)
    step_num = Column(Integer, nullable=False)
    agent_name = Column(String, nullable=True)
    artifact_type = Column(String, nullable=True)
    artifact_id = Column(String, nullable=True)
    file_path = Column(Text, nullable=False)
    created_at = Column(Float, default=time.time)

    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "iteration_num", "step_num"],
            ["steps.run_id", "steps.iteration_num", "steps.step_num"],
            ondelete="CASCADE",
        ),
    )

    step = relationship("Step", back_populates="artifacts")


class CodeFile(Base):
    __tablename__ = "code_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    iteration_num = Column(Integer, nullable=False)
    relative_path = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=True)
    created_at = Column(Float, default=time.time)

    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "iteration_num"],
            ["iterations.run_id", "iterations.iteration_num"],
            ondelete="CASCADE",
        ),
    )

    iteration = relationship("Iteration", back_populates="code_files")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    iteration_num = Column(Integer, nullable=True)
    step_num = Column(Integer, nullable=True)
    agent_name = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    message = Column(Text, default="")
    data = Column(Text, nullable=True)  # JSON string
    created_at = Column(Float, default=time.time)

    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["runs.run_id"], ondelete="CASCADE"),
        Index("ix_events_run_id", "run_id"),
    )

    run = relationship("Run", back_populates="events")
