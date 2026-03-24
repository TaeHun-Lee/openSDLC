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


# --- Project ---

class ProjectInfo(BaseModel):
    project_id: str
    name: str
    description: str = ""
    created_at: float
    run_count: int = 0


class ProjectDetail(BaseModel):
    project_id: str
    name: str
    description: str = ""
    created_at: float
    runs: list[RunSummary] = Field(default_factory=list)


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


class StepDetailInfo(BaseModel):
    """Extended step info with LLM usage and timing."""
    step_num: int
    agent_name: str
    mode: str | None = None
    verdict: str | None = None
    model_used: str | None = None
    provider: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None
    rework_seq: int = 0
    started_at: float | None = None
    finished_at: float | None = None
    artifacts: list[ArtifactRef] = Field(default_factory=list)


class ArtifactRef(BaseModel):
    """Artifact file reference (no content — use /artifacts endpoint for content)."""
    artifact_type: str | None = None
    artifact_id: str | None = None
    file_path: str


class CodeFileRef(BaseModel):
    """Code file reference."""
    relative_path: str
    file_path: str
    size_bytes: int | None = None


class IterationInfo(BaseModel):
    """Iteration summary for tree view."""
    iteration_num: int
    status: str = "running"
    satisfaction_score: int | None = None
    started_at: float | None = None
    finished_at: float | None = None
    steps: list[StepDetailInfo] = Field(default_factory=list)
    code_files: list[CodeFileRef] = Field(default_factory=list)


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
    project_id: str | None = None
    created_at: float
    finished_at: float | None = None
    iterations: list[IterationInfo] = Field(default_factory=list)
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


class EventInfo(BaseModel):
    """Single event for log/timeline views."""
    id: int
    event_type: str
    agent_name: str | None = None
    message: str | None = None
    iteration_num: int | None = None
    created_at: float


# --- Progress ---

class ProgressInfo(BaseModel):
    """Real-time progress snapshot for a running pipeline."""
    run_id: str
    status: str
    current_iteration: int | None = None
    current_step: int | None = None
    current_agent: str | None = None
    steps_total: int | None = None
    elapsed_seconds: float | None = None


# --- Health ---

class HealthResponse(BaseModel):
    status: str = "ok"
    llm_provider: str = ""
    model: str = ""


# Fix forward references — ProjectDetail uses RunSummary which is defined after it
ProjectDetail.model_rebuild()
StepDetailInfo.model_rebuild()
