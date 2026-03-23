"""Generic pipeline state for dynamic agent pipelines."""

from __future__ import annotations

from typing import TypedDict


class ReportingEvent(TypedDict, total=False):
    """Structured reporting event parsed from agent narrative."""
    event_type: str                     # "stage_started"|"artifact_completed"|"handoff"|"blocker_detected"
    agent_id: str                       # e.g. "ReqAgent"
    message: str                        # original matched text
    target_agent: str                   # handoff target (for handoff events)


class StepResult(TypedDict):
    """Output of a single pipeline step."""
    step_id: str                        # e.g. "step_1_ReqAgent"
    agent_id: str                       # e.g. "ReqAgent"
    artifact_yaml: str                  # raw YAML output from LLM
    artifact_type: str                  # e.g. "UseCaseModelArtifact"
    model_used: str                     # actual model used for this step
    validation_result: str | None       # ValidatorAgent only: "pass"|"warning"|"fail"
    narrative: str                      # agent's progress report text (pre/post artifact)
    reporting_events: list[ReportingEvent]  # structured events parsed from narrative


class PipelineState(TypedDict):
    """State that flows through the dynamic LangGraph pipeline."""
    user_story: str                             # original user input
    steps_completed: list[StepResult]           # ordered audit trail
    latest_artifacts: dict[str, str]            # artifact_type → latest YAML string
    current_step_index: int                     # position in pipeline definition
    iteration_count: int                        # spiral iteration (full pipeline cycle)
    max_iterations: int                         # max spiral iterations
    rework_count: int                           # per-gate rework counter (resets each gate)
    max_reworks_per_gate: int                   # max reworks allowed per validation gate
    pipeline_status: str                        # "running" | "completed" | "max_retries_exceeded"
