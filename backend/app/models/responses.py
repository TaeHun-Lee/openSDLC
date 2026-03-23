"""Pydantic response models for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Pipeline ---

class StepInfo(BaseModel):
    step: int
    agent: str
    model: str | None = None
    provider: str | None = None
    on_fail: str | None = None
    mode: str | None = None


class PipelineInfo(BaseModel):
    name: str
    description: str = ""
    max_iterations: int
    max_reworks_per_gate: int
    steps: list[StepInfo]
    is_default: bool = False


class PipelineListItem(BaseModel):
    name: str
    description: str = ""
    step_count: int
    is_default: bool = False


# --- Agent ---

class AgentInfo(BaseModel):
    agent_id: str
    display_name: str
    role: str
    primary_inputs: list[str] = Field(default_factory=list)
    primary_outputs: list[str] = Field(default_factory=list)


# --- Run ---

class RunCreated(BaseModel):
    run_id: str
    status: str
    pipeline: str


class StepResultInfo(BaseModel):
    step_id: str
    agent_id: str
    artifact_type: str
    model_used: str
    validation_result: str | None = None
    narrative: str = ""


class RunSummary(BaseModel):
    run_id: str
    pipeline_name: str
    status: str
    created_at: float
    finished_at: float | None = None
    steps_completed: int = 0
    error: str | None = None


class RunDetail(BaseModel):
    run_id: str
    pipeline_name: str
    user_story: str
    status: str
    max_iterations: int
    created_at: float
    finished_at: float | None = None
    steps: list[StepResultInfo] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class ArtifactInfo(BaseModel):
    artifact_type: str
    artifact_id: str | None = None
    yaml_content: str


class CodeFileInfo(BaseModel):
    path: str
    language: str
    content: str


class RunArtifacts(BaseModel):
    run_id: str
    artifacts: list[ArtifactInfo] = Field(default_factory=list)
    code_files: list[CodeFileInfo] = Field(default_factory=list)
    runtime_info: dict[str, str] = Field(default_factory=dict)


# --- Health ---

class HealthResponse(BaseModel):
    status: str = "ok"
    llm_provider: str = ""
    model: str = ""
