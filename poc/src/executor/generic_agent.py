"""Generic agent executor — single factory that creates LangGraph nodes for any agent."""

from __future__ import annotations

import re
import logging
from collections.abc import Callable

from registry.models import AgentConfig, StepDefinition
from registry.agent_registry import get_agent
from prompts.builder import build_system_prompt
from prompts.message_strategies import build_user_message
from llm_client import call_llm
from artifacts.parser import split_narrative_and_yaml, parse_artifact, get_validation_result
from reporting.event_parser import parse_reporting_events
from pipeline.state import PipelineState, StepResult

logger = logging.getLogger(__name__)

# Regex to detect if a line starts with [AgentName] bracket prefix
_BRACKET_PREFIX_RE = re.compile(r"^\[(\w+(?:Agent)?)\]")


def _resolve_output_type(agent_config: AgentConfig, step: StepDefinition) -> str:
    """Determine the artifact type this step produces from config."""
    # Prefer Artifact-typed outputs
    artifact_outputs = [o for o in agent_config.primary_outputs if o.endswith("Artifact")]
    if artifact_outputs:
        # TestAgent dual mode: filter by step.mode
        if step.mode and len(artifact_outputs) > 1:
            if step.mode == "design":
                return next((o for o in artifact_outputs if "Design" in o), artifact_outputs[0])
            elif step.mode == "execution":
                return next((o for o in artifact_outputs if "Report" in o), artifact_outputs[-1])
        return artifact_outputs[0]

    # Non-Artifact outputs (e.g. PMAgent's "iteration_assessment_{NN}.md")
    if agent_config.primary_outputs:
        return agent_config.primary_outputs[0]

    return "UnknownArtifact"


def _format_narrative(narrative: str, agent_id: str) -> str:
    """Ensure narrative lines follow the [AgentName] prefix convention.

    If the LLM didn't use bracket format, prepend [AgentId] to each
    substantive line so the output is consistent.
    """
    if not narrative:
        return narrative

    lines = narrative.splitlines()
    formatted: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted.append("")
            continue
        # Already has [AgentName] prefix — keep as-is
        if _BRACKET_PREFIX_RE.match(stripped):
            formatted.append(stripped)
        else:
            formatted.append(f"[{agent_id}] {stripped}")
    return "\n".join(formatted)


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
    output_type = _resolve_output_type(agent_config, step)

    def node_fn(state: PipelineState) -> dict:
        user_message = build_user_message(agent_config, step, state)

        response = call_llm(
            system=system_prompt,
            user_message=user_message,
            model=step.model,
            provider=step.provider,
            max_tokens=step.max_tokens,
            min_response_chars=step.min_response_chars,
        )

        # Split response into narrative (agent report) and YAML artifact
        narrative, artifact_yaml = split_narrative_and_yaml(response.text)

        # Display agent narrative to user (the agent's own voice)
        if narrative:
            formatted = _format_narrative(narrative, step.agent)
            print(f"\n{formatted}")
        else:
            # Fallback: minimal progress indicator if agent didn't produce narrative
            print(f"\n[{step.agent}] Step {step.step} ({output_type})")

        # Parse structured reporting events from narrative
        reporting_events = parse_reporting_events(narrative)
        for event in reporting_events:
            logger.debug(
                "[Reporting] %s: %s — %s",
                event.get("agent_id"),
                event.get("event_type"),
                event.get("message", "")[:80],
            )

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
            # Print validation verdict prominently
            verdict_symbol = {"pass": "PASS", "warning": "WARNING", "fail": "FAIL"}.get(
                validation_result, validation_result
            )
            print(f"[{step.agent}] 판정: {verdict_symbol}")

        step_result = StepResult(
            step_id=step_node_id,
            agent_id=step.agent,
            artifact_yaml=artifact_yaml,
            artifact_type=output_type,
            model_used=response.model,
            validation_result=validation_result,
            narrative=narrative,
            reporting_events=reporting_events,
        )

        new_latest = {**state["latest_artifacts"], output_type: artifact_yaml}
        new_steps = [*state["steps_completed"], step_result]

        # Rework counter: per-gate (increments on fail/warning, resets on pass)
        new_rework = state["rework_count"]
        if step.agent == "ValidatorAgent":
            if validation_result in ("fail", "warning"):
                new_rework += 1
            else:
                new_rework = 0  # reset on pass — gate cleared

        return {
            "steps_completed": new_steps,
            "latest_artifacts": new_latest,
            "rework_count": new_rework,
        }

    node_fn.__name__ = step_node_id
    return node_fn
