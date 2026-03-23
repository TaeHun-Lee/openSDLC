"""Generic agent executor — single factory that creates LangGraph nodes for any agent."""

from __future__ import annotations

import re
import logging
from collections.abc import Callable

from app.core.registry.models import AgentConfig, StepDefinition
from app.core.registry.agent_registry import get_agent
from app.core.prompts.builder import build_system_prompt
from app.core.prompts.message_strategies import build_user_message
from app.core.llm_client import call_llm
from app.core.artifacts.parser import split_narrative_and_yaml, parse_artifact, get_validation_result
from app.core.reporting.event_parser import parse_reporting_events
from app.core.pipeline.state import PipelineState, StepResult

logger = logging.getLogger(__name__)

_BRACKET_PREFIX_RE = re.compile(r"^\[(\w+(?:Agent)?)\]")
_ITERATION_DECISION_RE = re.compile(
    r"ITERATION_DECISION:\s*(continue|done)", re.IGNORECASE
)
_SATISFACTION_SCORE_RE = re.compile(
    r"SATISFACTION_SCORE:\s*(\d+)", re.IGNORECASE
)


def _resolve_output_type(agent_config: AgentConfig, step: StepDefinition) -> str:
    """Determine the artifact type this step produces from config."""
    artifact_outputs = [o for o in agent_config.primary_outputs if o.endswith("Artifact")]
    if artifact_outputs:
        if step.mode and len(artifact_outputs) > 1:
            if step.mode == "design":
                return next((o for o in artifact_outputs if "Design" in o), artifact_outputs[0])
            elif step.mode == "execution":
                return next((o for o in artifact_outputs if "Report" in o), artifact_outputs[-1])
        return artifact_outputs[0]

    if agent_config.primary_outputs:
        return agent_config.primary_outputs[0]

    return "UnknownArtifact"


def _format_narrative(narrative: str, agent_id: str) -> str:
    """Ensure narrative lines follow the [AgentName] prefix convention."""
    if not narrative:
        return narrative

    lines = narrative.splitlines()
    formatted: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted.append("")
            continue
        if _BRACKET_PREFIX_RE.match(stripped):
            formatted.append(stripped)
        else:
            formatted.append(f"[{agent_id}] {stripped}")
    return "\n".join(formatted)


def _extract_pm_decision(text: str) -> str:
    """Extract ITERATION_DECISION from PMAgent output. Defaults to 'continue'."""
    m = _ITERATION_DECISION_RE.search(text)
    if m:
        return m.group(1).lower()
    logger.warning("[PMAgent] ITERATION_DECISION not found in output — defaulting to 'continue'")
    return "continue"


def _extract_satisfaction_score(text: str) -> int:
    """Extract SATISFACTION_SCORE from PMAgent output. Defaults to 0."""
    m = _SATISFACTION_SCORE_RE.search(text)
    if m:
        return int(m.group(1))
    return 0


def create_agent_node(
    step: StepDefinition,
) -> Callable[[PipelineState], dict]:
    """Factory: create a LangGraph node function for a given pipeline step."""
    agent_config = get_agent(step.agent)
    system_prompt = build_system_prompt(agent_config, step)
    step_node_id = f"step_{step.step}_{step.agent}"
    output_type = _resolve_output_type(agent_config, step)

    def node_fn(state: PipelineState) -> dict:
        resolved_output_type = output_type.replace(
            "{NN}", f"{state['iteration_count']:02d}"
        )

        user_message = build_user_message(agent_config, step, state)

        response = call_llm(
            system=system_prompt,
            user_message=user_message,
            model=step.model,
            provider=step.provider,
            max_tokens=step.max_tokens,
            min_response_chars=step.min_response_chars,
        )

        narrative, artifact_yaml = split_narrative_and_yaml(response.text)

        if narrative:
            formatted = _format_narrative(narrative, step.agent)
            print(f"\n{formatted}")
        else:
            print(f"\n[{step.agent}] Step {step.step} ({resolved_output_type})")

        reporting_events = parse_reporting_events(narrative)
        for event in reporting_events:
            logger.debug(
                "[Reporting] %s: %s — %s",
                event.get("agent_id"),
                event.get("event_type"),
                event.get("message", "")[:80],
            )

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
            verdict_symbol = {"pass": "PASS", "warning": "WARNING", "fail": "FAIL"}.get(
                validation_result, validation_result
            )
            print(f"[{step.agent}] 판정: {verdict_symbol}")

        step_result = StepResult(
            step_id=step_node_id,
            agent_id=step.agent,
            artifact_yaml=artifact_yaml,
            artifact_type=resolved_output_type,
            model_used=response.model,
            validation_result=validation_result,
            narrative=narrative,
            reporting_events=reporting_events,
        )

        new_latest = {**state["latest_artifacts"], resolved_output_type: artifact_yaml}
        new_steps = [*state["steps_completed"], step_result]

        new_rework = state["rework_count"]
        if step.agent == "ValidatorAgent":
            if validation_result in ("fail", "warning"):
                new_rework += 1
            else:
                new_rework = 0

        state_update: dict = {
            "steps_completed": new_steps,
            "latest_artifacts": new_latest,
            "rework_count": new_rework,
        }

        # PMAgent iteration decision extraction
        if step.on_next_iteration and step.agent == "PMAgent":
            full_text = response.text
            pm_decision = _extract_pm_decision(full_text)
            score = _extract_satisfaction_score(full_text)
            decision_label = {"continue": "CONTINUE (다음 iteration)", "done": "DONE (완료)"}.get(
                pm_decision, pm_decision
            )
            print(f"[{step.agent}] Iteration 판정: {decision_label} (만족도: {score}/100)")
            state_update["pm_decision"] = pm_decision

            # Increment iteration_count when continuing
            if pm_decision == "continue":
                state_update["iteration_count"] = state["iteration_count"] + 1
                # Reset rework counter for new iteration
                state_update["rework_count"] = 0

        return state_update

    node_fn.__name__ = step_node_id
    return node_fn
