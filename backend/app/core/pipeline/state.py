"""Generic pipeline state for dynamic agent pipelines."""

from __future__ import annotations

from typing import TypedDict


class ReportingEvent(TypedDict, total=False):
    """Structured reporting event parsed from agent narrative."""

    event_type: str
    agent_id: str
    message: str
    target_agent: str


class StepResult(TypedDict):
    """Output of a single pipeline step."""

    step_id: str
    agent_id: str
    artifact_yaml: str
    artifact_type: str
    model_used: str
    validation_result: str | None
    narrative: str
    reporting_events: list[ReportingEvent]


class PipelineState(TypedDict):
    """State that flows through the dynamic LangGraph pipeline."""

    user_story: str
    steps_completed: list[StepResult]
    latest_artifacts: dict[str, str]
    current_step_index: int
    iteration_count: int
    max_iterations: int
    rework_count: int
    max_reworks_per_gate: int
    pipeline_status: str
    pm_decision: str                        # PMAgent iteration decision: "continue" | "done" | ""
