"""Generic pipeline state for dynamic agent pipelines."""

from __future__ import annotations

from typing import TypedDict


class StepResult(TypedDict):
    """Output of a single pipeline step."""
    step_id: str                        # e.g. "step_1_ReqAgent"
    agent_id: str                       # e.g. "ReqAgent"
    artifact_yaml: str                  # raw YAML output from LLM
    artifact_type: str                  # e.g. "UseCaseModelArtifact"
    model_used: str                     # actual model used for this step
    validation_result: str | None       # ValidatorAgent only: "pass"|"warning"|"fail"


class PipelineState(TypedDict):
    """State that flows through the dynamic LangGraph pipeline."""
    user_story: str                             # original user input
    steps_completed: list[StepResult]           # ordered audit trail
    latest_artifacts: dict[str, str]            # artifact_type → latest YAML string
    current_step_index: int                     # position in pipeline definition
    iteration_count: int                        # global rework counter
    max_iterations: int                         # hard limit
    pipeline_status: str                        # "running" | "completed" | "max_retries_exceeded"
