"""User message build strategies for each agent type.

Replaces the if/elif chain in generic_agent.py with a strategy pattern.
Each strategy function takes (agent_config, step, state) and returns a user message string.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from registry.models import AgentConfig, StepDefinition
    from pipeline.state import PipelineState


def _strategy_req_agent(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    latest = state["latest_artifacts"]
    if not latest.get("ValidationReportArtifact"):
        return (
            "[PMAgent] 아래 User Story를 분석하여 UseCaseModelArtifact를 작성하라.\n\n"
            f"User Story:\n{state['user_story']}"
        )
    return (
        "[PMAgent] ValidatorAgent가 아래 사유로 이전 artifact를 반려하였다.\n"
        "해당 사유만 수정하여 개선된 UseCaseModelArtifact를 재작성하라.\n\n"
        f"ValidationReport:\n{latest.get('ValidationReportArtifact', '')}\n\n"
        f"이전 UC Artifact:\n{latest.get('UseCaseModelArtifact', '')}\n\n"
        f"원본 User Story:\n{state['user_story']}"
    )


def _strategy_validator(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    """ValidatorAgent: only receives the target artifact YAML (context isolation)."""
    latest = state["latest_artifacts"]
    # Find the most recent non-validation artifact type
    target_type = "UseCaseModelArtifact"
    for step_result in reversed(state["steps_completed"]):
        if step_result["agent_id"] != "ValidatorAgent":
            target_type = step_result["artifact_type"]
            break
    target_yaml = latest.get(target_type, "")
    return (
        f"아래 {target_type}를 검증하고 ValidationReportArtifact를 작성하라.\n"
        "이 artifact 외의 정보(이전 agent의 사고 과정 등)는 참조하지 말 것.\n\n"
        f"{target_type}:\n{target_yaml}"
    )


def _strategy_input_assembler(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    """Generic strategy: assemble primary_inputs from latest artifacts."""
    latest = state["latest_artifacts"]
    output_name = agent_config.primary_outputs[0] if agent_config.primary_outputs else "artifact"
    parts = [f"아래 승인된 artifacts를 기반으로 {output_name}를 작성하라.\n"]
    for input_name in agent_config.primary_inputs:
        # Match artifact types in latest_artifacts (skip non-artifact inputs like "user request")
        if input_name in latest and latest[input_name]:
            parts.append(f"{input_name}:\n{latest[input_name]}\n")
    # Fallback: if no artifacts matched via primary_inputs, dump all available
    if len(parts) == 1:
        for atype, ayaml in latest.items():
            if ayaml:
                parts.append(f"{atype}:\n{ayaml}\n")
    return "\n".join(parts)


def _strategy_test_agent(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    latest = state["latest_artifacts"]
    mode = step.mode or "design"
    if mode == "design":
        return (
            "아래 UseCaseModelArtifact를 기반으로 TestDesignArtifact를 작성하라.\n\n"
            f"UseCaseModelArtifact:\n{latest.get('UseCaseModelArtifact', '')}"
        )
    return (
        "아래 artifacts를 기반으로 TestReportArtifact를 작성하라.\n\n"
        f"TestDesignArtifact:\n{latest.get('TestDesignArtifact', '')}\n\n"
        f"ImplementationArtifact:\n{latest.get('ImplementationArtifact', '')}"
    )


_STRATEGIES: dict[str, callable] = {
    "req_agent": _strategy_req_agent,
    "validator": _strategy_validator,
    "input_assembler": _strategy_input_assembler,
    "test_agent": _strategy_test_agent,
}


def build_user_message(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    """Build user message using the strategy specified in agent_config."""
    strategy_key = agent_config.user_message_strategy
    strategy_fn = _STRATEGIES.get(strategy_key)
    if strategy_fn is None:
        raise ValueError(
            f"Unknown user_message_strategy: {strategy_key!r}. "
            f"Available: {list(_STRATEGIES)}"
        )
    return strategy_fn(agent_config, step, state)
