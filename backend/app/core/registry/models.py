"""Pydantic models for agent configs and pipeline definitions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AgentPersona(BaseModel):
    """Agent persona from config YAML."""

    codename: str = ""
    mission: str = ""
    tone: str = ""
    strengths: list[str] = Field(default_factory=list)
    behavioral_rules: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Parsed agent configuration from *.config.yaml."""

    model_config = ConfigDict(extra="allow")

    agent_id: str
    display_name: str
    role: str
    system_scope: str = ""
    base_prompt_files: list[str] = Field(default_factory=list)
    primary_inputs: list[str] = Field(default_factory=list)
    primary_outputs: list[str] = Field(default_factory=list)
    handoff_rules: dict = Field(default_factory=dict)
    persona: AgentPersona = Field(default_factory=AgentPersona)
    success_definition: list[str] = Field(default_factory=list)

    constitution_sections: list[str] = Field(default_factory=list)
    reference_templates: list[str] = Field(default_factory=list)
    mandate_files: list[str] = Field(default_factory=list)
    user_message_strategy: str = "input_assembler"


class StepDefinition(BaseModel):
    """One step in a user-defined pipeline."""

    step: int
    agent: str
    model: str | None = None
    provider: str | None = None
    on_fail: str | None = None
    on_next_iteration: str | None = None    # PMAgent: agent_id to restart iteration
    mode: str | None = None
    max_tokens: int = 8192
    min_response_chars: int = 1000
    extra_templates: list[str] | None = None
    user_message_strategy: str | None = None  # Override agent config's strategy for this step
    extra_mandate_files: list[str] | None = None  # Additional mandates for this step


class PipelineDefinition(BaseModel):
    """Complete user-defined pipeline."""

    name: str
    description: str = ""
    max_iterations: int = 3
    max_reworks_per_gate: int = 3
    steps: list[StepDefinition]
