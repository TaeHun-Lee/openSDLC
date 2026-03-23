"""Pydantic models for agent configs and pipeline definitions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentPersona(BaseModel):
    """Agent persona from config YAML."""
    codename: str = ""
    mission: str = ""
    tone: str = ""
    strengths: list[str] = Field(default_factory=list)
    behavioral_rules: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Parsed agent configuration from *.config.yaml."""
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

    # PoC overlay fields (populated from agent-config-overrides/)
    constitution_sections: list[str] = Field(default_factory=list)
    reference_templates: list[str] = Field(default_factory=list)
    mandate_files: list[str] = Field(default_factory=list)
    user_message_strategy: str = "input_assembler"

    class Config:
        extra = "allow"


class StepDefinition(BaseModel):
    """One step in a user-defined pipeline."""
    step: int
    agent: str                                  # agent_id from registry
    model: str | None = None                    # LLM model override
    provider: str | None = None                 # LLM provider override
    on_fail: str | None = None                  # ValidatorAgent: agent_id to rework to
    mode: str | None = None                     # TestAgent: "design" | "execution"
    max_tokens: int = 8192
    min_response_chars: int = 1000
    extra_templates: list[str] | None = None    # additional template names


class PipelineDefinition(BaseModel):
    """Complete user-defined pipeline."""
    name: str
    description: str = ""
    max_iterations: int = 3              # max full spiral iterations
    max_reworks_per_gate: int = 3        # max rework retries per validation gate
    steps: list[StepDefinition]
