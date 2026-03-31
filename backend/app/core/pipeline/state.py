"""Generic pipeline state for dynamic agent pipelines."""

from __future__ import annotations

from typing import TypedDict


class ReportingEvent(TypedDict, total=False):
    """Structured reporting event parsed from agent narrative."""

    event_type: str
    agent_id: str
    message: str
    target_agent: str


class _StepResultRequired(TypedDict):
    """Required fields for a pipeline step result."""

    step_id: str
    agent_id: str
    artifact_yaml: str
    artifact_type: str
    model_used: str
    validation_result: str | None
    narrative: str
    reporting_events: list[ReportingEvent]


class StepResult(_StepResultRequired, total=False):
    """Output of a single pipeline step (with optional tracking fields)."""

    # LLM usage tracking
    provider: str
    input_tokens: int | None
    output_tokens: int | None
    cache_read_tokens: int | None
    cache_creation_tokens: int | None
    # Timing
    started_at: float
    finished_at: float
    # Position tracking
    step_num: int
    iteration_num: int
    rework_seq: int
    # PMAgent evaluation
    satisfaction_score: int


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
    pm_action_type: str                     # PMAgent action decision: "new" | "modify" | ""
    latest_code_blocks: dict[str, str]      # agent_id → code block text (<!-- FILE: --> markers)
    workspace_context: dict[str, str]       # path → content (existing files in workspace)
