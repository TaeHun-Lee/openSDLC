"""Pydantic request models for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StartRunRequest(BaseModel):
    """Request body for POST /api/runs."""

    pipeline: str = Field(
        ...,
        description="Pipeline name (e.g. 'full_spiral') or file path",
        min_length=1,
        examples=["full_spiral"],
    )
    user_story: str = Field(
        ...,
        description="User story text to process",
        min_length=10,
        examples=["간단한 할 일 관리 웹 앱을 만들어줘. 할 일 추가, 완료 체크, 삭제 기능이 필요해."],
    )
    workspace_path: str | None = Field(
        None,
        description="Optional path to an existing workspace to analyze and potentially modify",
        examples=["/path/to/my-existing-project"],
    )
    max_iterations: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Maximum rework iterations",
        examples=[1],
    )
    project_id: str | None = Field(
        None,
        description="Project ID to associate this run with",
    )
    webhook_url: str | None = Field(
        None,
        description="URL to receive POST notification on run completion/failure/cancellation",
        examples=["https://example.com/hooks/opensdlc"],
    )
    webhook_events: list[str] | None = Field(
        None,
        description="Event types to notify: completed, failed, cancelled. Defaults to all.",
        examples=[["completed", "failed"]],
    )


# --- Projects ---


class CreateProjectRequest(BaseModel):
    """Request body for POST /api/projects."""

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: str = Field("", max_length=500)


class UpdateProjectRequest(BaseModel):
    """Request body for PUT /api/projects/{project_id}."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


# --- Pipeline Editor ---


class PipelineStepInput(BaseModel):
    """One step in a user-defined pipeline.

    Users provide agent + optional overrides.
    Step numbers and on_fail are computed server-side.
    """

    agent: str = Field(..., description="Agent ID (e.g. 'ReqAgent', 'ValidatorAgent')")
    model: str | None = Field(None, description="LLM model override (e.g. 'claude-sonnet-4-6')")
    provider: str | None = Field(
        None,
        description="LLM provider override: anthropic|google|openai|ollama",
    )
    mode: str | None = Field(None, description="TestAgent only: 'design' or 'execution'")
    max_tokens: int = Field(8192, ge=1024, le=65536, description="Max output tokens for this step")


class CreatePipelineRequest(BaseModel):
    """Request body for POST /api/pipelines."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$",
        description="Pipeline name (alphanumeric, hyphens, underscores)",
    )
    description: str = Field("", max_length=500)
    max_iterations: int = Field(3, ge=1, le=10, description="Max spiral iterations")
    max_reworks_per_gate: int = Field(3, ge=1, le=10, description="Max reworks per validation gate")
    steps: list[PipelineStepInput] = Field(..., min_length=1, max_length=30)


class UpdatePipelineRequest(BaseModel):
    """Request body for PUT /api/pipelines/{name}.

    All fields optional — only provided fields are updated.
    If steps is provided, the entire step list is replaced and recompiled.
    """

    description: str | None = Field(None, max_length=500)
    max_iterations: int | None = Field(None, ge=1, le=10)
    max_reworks_per_gate: int | None = Field(None, ge=1, le=10)
    steps: list[PipelineStepInput] | None = Field(None, min_length=1, max_length=30)
