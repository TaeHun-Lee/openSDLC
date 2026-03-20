"""Generic agent executor — single factory that creates LangGraph nodes for any agent."""

from __future__ import annotations

import logging
from collections.abc import Callable

from registry.models import AgentConfig, StepDefinition
from registry.agent_registry import get_agent
from prompts.builder import build_system_prompt
from llm_client import call_llm
from artifacts.parser import extract_yaml_from_response, parse_artifact, get_validation_result
from pipeline.state import PipelineState, StepResult

logger = logging.getLogger(__name__)

# Agent → output artifact type
_AGENT_OUTPUT_MAP: dict[str, str] = {
    "ReqAgent": "UseCaseModelArtifact",
    "ValidatorAgent": "ValidationReportArtifact",
    "CodeAgent": "ImplementationArtifact",
    "CoordAgent": "FeedbackArtifact",
    "PMAgent": "VerificationReport",
}


def _resolve_output_type(agent_id: str, step: StepDefinition) -> str:
    """Determine the artifact type this step produces."""
    if agent_id == "TestAgent":
        mode = step.mode or "design"
        return "TestDesignArtifact" if mode == "design" else "TestReportArtifact"
    return _AGENT_OUTPUT_MAP.get(agent_id, "UnknownArtifact")


def _find_validation_target(state: PipelineState) -> str:
    """Find the artifact type the ValidatorAgent should validate.

    Looks at the most recent non-validation step result.
    """
    for step_result in reversed(state["steps_completed"]):
        if step_result["agent_id"] != "ValidatorAgent":
            return step_result["artifact_type"]
    return "UseCaseModelArtifact"


def _build_user_message(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    """Build the user message for any agent, respecting context isolation.

    Context isolation rule: only pass artifact YAML strings,
    never system prompts or reasoning from other agents.
    """
    agent_id = agent_config.agent_id
    latest = state["latest_artifacts"]

    if agent_id == "ReqAgent":
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

    if agent_id == "ValidatorAgent":
        target_type = _find_validation_target(state)
        target_yaml = latest.get(target_type, "")
        return (
            f"아래 {target_type}를 검증하고 ValidationReportArtifact를 작성하라.\n"
            "이 artifact 외의 정보(이전 agent의 사고 과정 등)는 참조하지 말 것.\n\n"
            f"{target_type}:\n{target_yaml}"
        )

    if agent_id == "CodeAgent":
        parts = [
            "아래 승인된 artifacts를 기반으로 ImplementationArtifact를 작성하라.\n",
        ]
        if latest.get("UseCaseModelArtifact"):
            parts.append(
                f"UseCaseModelArtifact:\n{latest['UseCaseModelArtifact']}\n"
            )
        if latest.get("TestDesignArtifact"):
            parts.append(
                f"TestDesignArtifact:\n{latest['TestDesignArtifact']}\n"
            )
        return "\n".join(parts)

    if agent_id == "TestAgent":
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

    if agent_id == "CoordAgent":
        return (
            "아래 TestReportArtifact를 기반으로 FeedbackArtifact를 작성하라.\n\n"
            f"TestReportArtifact:\n{latest.get('TestReportArtifact', '')}"
        )

    # PMAgent or unknown: pass all available artifacts
    parts = ["Available artifacts:\n"]
    for atype, ayaml in latest.items():
        parts.append(f"--- {atype} ---\n{ayaml}\n")
    return "\n".join(parts)


def create_agent_node(
    step: StepDefinition,
) -> Callable[[PipelineState], dict]:
    """Factory: create a LangGraph node function for a given pipeline step.

    Returns a closure that captures the step config and agent config.
    The returned function takes PipelineState and returns a partial state update dict.
    """
    agent_config = get_agent(step.agent)
    system_prompt = build_system_prompt(agent_config, step)
    step_node_id = f"step_{step.step}_{step.agent}"
    output_type = _resolve_output_type(step.agent, step)

    def node_fn(state: PipelineState) -> dict:
        print(f"\n[{step.agent}] Step {step.step} 시작 ({output_type})")

        user_message = _build_user_message(agent_config, step, state)

        response = call_llm(
            system=system_prompt,
            user_message=user_message,
            model=step.model,
            provider=step.provider,
            max_tokens=step.max_tokens,
            min_response_chars=step.min_response_chars,
        )

        artifact_yaml = extract_yaml_from_response(response.text)

        # For ValidatorAgent, extract validation_result
        validation_result: str | None = None
        if step.agent == "ValidatorAgent":
            report_dict = None
            try:
                report_dict = parse_artifact(artifact_yaml)
            except Exception as exc:
                logger.warning(
                    "[%s] YAML parse failed: %s — using regex fallback",
                    step.agent,
                    exc,
                )
            validation_result = get_validation_result(report_dict, raw_yaml=artifact_yaml)

        step_result = StepResult(
            step_id=step_node_id,
            agent_id=step.agent,
            artifact_yaml=artifact_yaml,
            artifact_type=output_type,
            model_used=response.model,
            validation_result=validation_result,
        )

        new_latest = {**state["latest_artifacts"], output_type: artifact_yaml}
        new_steps = [*state["steps_completed"], step_result]

        # Increment iteration count on validation fail/warning
        new_iteration = state["iteration_count"]
        if step.agent == "ValidatorAgent" and validation_result in ("fail", "warning"):
            new_iteration += 1

        print(
            f"[{step.agent}] Step {step.step} 완료"
            + (f" → 판정: {validation_result.upper()}" if validation_result else "")
        )

        return {
            "steps_completed": new_steps,
            "latest_artifacts": new_latest,
            "iteration_count": new_iteration,
        }

    node_fn.__name__ = step_node_id
    return node_fn
