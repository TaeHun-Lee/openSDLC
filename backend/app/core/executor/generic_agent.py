"""Generic agent executor — single factory that creates LangGraph nodes for any agent."""

from __future__ import annotations

import re
import logging
import threading
import time
from collections.abc import Callable

from app.core.registry.models import AgentConfig, StepDefinition
from app.core.registry.agent_registry import get_agent
from app.core.prompts.builder import build_system_prompt
from app.core.prompts.message_strategies import build_user_message
from app.core.llm_client import call_llm
from app.core.artifacts.parser import (
    parse_artifact,
    parse_artifact_checked,
    parse_step_output,
    get_validation_result,
    extract_code_blocks_from_narrative,
    strip_code_blocks_from_narrative,
)
from app.core.artifacts.code_extractor import merge_code_blocks
from app.core.reporting.event_parser import parse_reporting_events
from app.core.pipeline.state import PipelineState, StepResult
from app.services.event_bus import EventType, RunEvent
from app.services.print_capture import get_artifact_saver, get_cancel_event, get_event_emitter

logger = logging.getLogger(__name__)

_BRACKET_PREFIX_RE = re.compile(r"^\[(\w+(?:Agent)?)\]")

# --- PM decision extraction patterns (robust against LLM formatting variations) ---

# Strip markdown code fences, bold markers, and backticks before pattern matching
_MARKDOWN_NOISE_RE = re.compile(r"```(?:yaml|json|text|markdown)?\s*\n?|```|[`*]")

# Allow flexible separators: "ITERATION_DECISION: continue", "ITERATION_DECISION = done",
# "ITERATION_DECISION - continue", with optional quotes around the value
_ITERATION_DECISION_RE = re.compile(
    r"ITERATION[_\s-]*DECISION\s*[:=\-]\s*[\"']?(continue|done)[\"']?",
    re.IGNORECASE,
)
_SATISFACTION_SCORE_RE = re.compile(
    r"SATISFACTION[_\s-]*SCORE\s*[:=\-]\s*[\"']?(\d+)[\"']?",
    re.IGNORECASE,
)
_PM_ACTION_TYPE_RE = re.compile(
    r"PM[_\s-]*ACTION[_\s-]*TYPE\s*[:=\-]\s*[\"']?(new|modify)[\"']?",
    re.IGNORECASE,
)


def _resolve_output_mode(agent_config: AgentConfig, step: StepDefinition) -> str:
    """Resolve the runtime output mode for this step."""
    if step.output_mode:
        return step.output_mode
    artifact_outputs = [o for o in agent_config.primary_outputs if o.endswith("Artifact")]
    if artifact_outputs:
        return "yaml_artifact"
    if step.report_template and step.on_next_iteration:
        return "markdown_report"
    if step.agent == "PMAgent":
        return "narrative_only"
    return "yaml_artifact"


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


def _resolve_report_name(step: StepDefinition, state: PipelineState) -> str:
    """Resolve concrete report filename for markdown-report steps."""
    if not step.report_template:
        return ""
    return step.report_template.replace("{{iteration}}", f"{state['iteration_count']:02d}")


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


_MIN_FAILURE_CANDIDATES = 3


def _current_gate_rework_count(state: PipelineState, step: StepDefinition) -> int:
    """Get the rework count for the most recent validator gate relevant to this step."""
    rework_counts = state.get("rework_counts", {})
    if step.agent == "ValidatorAgent":
        return rework_counts.get(step.step, 0)
    return max(rework_counts.values(), default=0)


def enforce_adversarial_mandate(
    validation_result: str,
    report_dict: dict | None,
) -> str:
    """Check adversarial mandate on ValidatorAgent pass verdicts.

    Logs a warning if the validation result is "pass" but fewer than 3
    failure_candidates are present.  Does NOT override the result — the
    mandate serves as diagnostic guidance, not a hard gate that blocks
    the pipeline.

    Returns the original validation result unchanged.
    """
    if validation_result != "pass" or not isinstance(report_dict, dict):
        return validation_result

    failure_candidates = report_dict.get("failure_candidates", [])
    if not isinstance(failure_candidates, list):
        failure_candidates = []

    if len(failure_candidates) < _MIN_FAILURE_CANDIDATES:
        logger.warning(
            "[ValidatorAgent] Adversarial mandate note: pass verdict accepted with "
            "only %d failure_candidates (recommended minimum %d). "
            "Consider improving the prompt to elicit more thorough analysis.",
            len(failure_candidates),
            _MIN_FAILURE_CANDIDATES,
        )
    else:
        logger.info(
            "[ValidatorAgent] Adversarial mandate satisfied: %d failure_candidates considered",
            len(failure_candidates),
        )
    return validation_result


# ---------------------------------------------------------------------------
# Event emission helper
# ---------------------------------------------------------------------------


def _emit(event: RunEvent) -> None:
    """Emit a structured event via the thread-local emitter (if available)."""
    emitter = get_event_emitter()
    if emitter is not None:
        try:
            emitter(event)
        except Exception:
            pass  # never break the pipeline due to emitter failure


# ---------------------------------------------------------------------------
# Resume replay — thread-local queue of already-completed steps
# ---------------------------------------------------------------------------
_replay_ctx = threading.local()


def set_replay_queue(steps: list[StepResult]) -> None:
    """Store ordered list of completed steps to replay during resume."""
    _replay_ctx.queue = list(steps)


def clear_replay_queue() -> None:
    """Discard the replay queue (resume point reached or cleanup)."""
    _replay_ctx.queue = None


def _try_replay(step: StepDefinition, state: PipelineState) -> dict | None:
    """If the next queued step matches this node, pop and return a state update.

    Returns None when the queue is empty or the front doesn't match,
    signalling that real LLM execution should proceed.
    """
    queue: list[StepResult] | None = getattr(_replay_ctx, "queue", None)
    if not queue:
        return None

    next_sr = queue[0]
    if (
        next_sr["agent_id"] != step.agent
        or next_sr.get("step_num") != step.step
        or next_sr.get("iteration_num") != state["iteration_count"]
        or next_sr.get("rework_seq", 0) != _current_gate_rework_count(state, step)
    ):
        return None

    # Match — pop from queue and build state update without LLM call
    sr = queue.pop(0)

    art_type = sr.get("artifact_type", "")
    art_yaml = sr.get("artifact_yaml", "")

    new_latest = {**state["latest_artifacts"]}
    if art_type and art_yaml:
        new_latest[art_type] = art_yaml

    new_steps = [*state["steps_completed"], sr]

    new_rework_counts = {**state.get("rework_counts", {})}
    if step.agent == "ValidatorAgent":
        gate_key = step.step
        current_gate_count = new_rework_counts.get(gate_key, 0)
        vr = sr.get("validation_result")
        if vr == "fail":
            new_rework_counts[gate_key] = current_gate_count + 1
        elif vr == "warning":
            new_rework_counts[gate_key] = current_gate_count
        elif vr == "pass":
            new_rework_counts[gate_key] = 0

    state_update: dict = {
        "steps_completed": new_steps,
        "latest_artifacts": new_latest,
        "rework_counts": new_rework_counts,
    }

    # PMAgent iteration decision — infer from remaining queue
    if step.on_next_iteration and step.agent == "PMAgent":
        current_iter = state["iteration_count"]
        has_next = any(s.get("iteration_num", 0) > current_iter for s in queue)
        if has_next:
            state_update["pm_decision"] = "continue"
            state_update["iteration_count"] = current_iter + 1
            state_update["rework_counts"] = {}
        else:
            state_update["pm_decision"] = "done"

    return state_update


def _strip_markdown_noise(text: str) -> str:
    """Remove markdown code fences, bold markers, and backticks that LLMs may wrap around values."""
    return _MARKDOWN_NOISE_RE.sub("", text)


def _extract_pm_decision(text: str) -> str:
    """Extract ITERATION_DECISION from PMAgent output. Defaults to 'continue'.

    Handles common LLM formatting variations:
    - Markdown code blocks wrapping the value
    - Extra whitespace or alternative separators (=, -)
    - Quoted values ("continue", 'done')
    """
    # Try raw text first (fastest path)
    m = _ITERATION_DECISION_RE.search(text)
    if m:
        return m.group(1).lower()

    # Retry after stripping markdown noise
    cleaned = _strip_markdown_noise(text)
    m = _ITERATION_DECISION_RE.search(cleaned)
    if m:
        logger.info("[PMAgent] ITERATION_DECISION found after markdown cleanup: %s", m.group(1))
        return m.group(1).lower()

    logger.warning("[PMAgent] ITERATION_DECISION not found in output — defaulting to 'continue'")
    return "continue"


def _extract_satisfaction_score(text: str) -> int:
    """Extract SATISFACTION_SCORE from PMAgent output. Defaults to 0.

    Handles the same formatting variations as _extract_pm_decision.
    """
    m = _SATISFACTION_SCORE_RE.search(text)
    if m:
        return int(m.group(1))

    cleaned = _strip_markdown_noise(text)
    m = _SATISFACTION_SCORE_RE.search(cleaned)
    if m:
        logger.info("[PMAgent] SATISFACTION_SCORE found after markdown cleanup: %s", m.group(1))
        return int(m.group(1))

    return 0


def _extract_pm_action_type(text: str) -> str:
    """Extract PM_ACTION_TYPE from PMAgent output. Defaults to 'new'.

    Expected values: 'new' | 'modify'
    """
    m = _PM_ACTION_TYPE_RE.search(text)
    if m:
        return m.group(1).lower()

    # Retry after stripping markdown noise
    cleaned = _strip_markdown_noise(text)
    m = _PM_ACTION_TYPE_RE.search(cleaned)
    if m:
        logger.info("[PMAgent] PM_ACTION_TYPE found after markdown cleanup: %s", m.group(1))
        return m.group(1).lower()

    return "new"


def create_agent_node(
    step: StepDefinition,
) -> Callable[[PipelineState], dict]:
    """Factory: create a LangGraph node function for a given pipeline step."""
    agent_config = get_agent(step.agent)
    system_prompt = build_system_prompt(agent_config, step)
    step_node_id = f"step_{step.step}_{step.agent}"
    output_mode = _resolve_output_mode(agent_config, step)
    output_type = _resolve_output_type(agent_config, step)

    def node_fn(state: PipelineState) -> dict:
        # Check for cancellation before starting each step
        cancel = get_cancel_event()
        if cancel is not None and cancel.is_set():
            raise InterruptedError(f"Run cancelled before step {step.step} ({step.agent})")

        # Resume replay: skip LLM call if this step was already completed
        replay_update = _try_replay(step, state)
        if replay_update is not None:
            logger.info(
                "[%s] Step %d replayed from resume state (iteration %d, rework %d)",
                step.agent, step.step, state["iteration_count"], _current_gate_rework_count(state, step),
            )
            return replay_update
        # Past the replay point — clear queue so subsequent nodes don't check
        clear_replay_queue()

        resolved_output_type = output_type.replace(
            "{NN}", f"{state['iteration_count']:02d}"
        )
        resolved_output_mode = output_mode
        resolved_report_name = _resolve_report_name(step, state)

        user_message = build_user_message(agent_config, step, state)

        # Determine which artifacts this agent consumes
        input_artifact_types = [
            k for k in agent_config.primary_inputs
            if k in state["latest_artifacts"]
        ]

        # Emit STEP_STARTED event directly to EventBus
        _emit(RunEvent(
            event_type=EventType.STEP_STARTED,
            data={
                "step_num": step.step,
                "agent_id": step.agent,
                "iteration_num": state["iteration_count"],
                "rework_seq": _current_gate_rework_count(state, step),
                "input_artifacts": input_artifact_types,
                "expected_output": resolved_report_name or resolved_output_type,
                "mode": step.mode,
                "message": f"[{step.agent}] Step {step.step} started",
            },
        ))

        started_at = time.time()
        response = call_llm(
            system=system_prompt,
            user_message=user_message,
            model=step.model,
            provider=step.provider,
            max_tokens=step.max_tokens,
            min_response_chars=step.min_response_chars,
        )
        finished_at = time.time()

        parsed = parse_step_output(response.text, output_mode=resolved_output_mode)
        narrative = parsed["narrative"]
        artifact_yaml = parsed["artifact_yaml"]
        report_body = parsed["report_body"]

        # Extract code blocks from narrative (for ImplementationArtifact)
        code_blocks: list[dict[str, str]] = []
        if resolved_output_mode == "yaml_artifact" and resolved_output_type.startswith("ImplementationArtifact"):
            code_blocks = extract_code_blocks_from_narrative(narrative)
            if code_blocks:
                logger.info(
                    "[%s] Extracted %d code blocks from narrative",
                    step.agent, len(code_blocks),
                )

        if resolved_output_mode == "yaml_artifact":
            narrative = strip_code_blocks_from_narrative(narrative)
        elif resolved_output_mode == "markdown_report" and report_body:
            # 비어있지 않은 줄 중 처음 5줄을 요약으로 사용 (기존 3줄 → 5줄)
            summary_lines = [line.strip() for line in report_body.splitlines() if line.strip()][:5]
            narrative = "\n".join(summary_lines)

        # Terminal logging + narrative event
        if narrative:
            formatted = _format_narrative(narrative, step.agent)
            print(f"\n{formatted}")
            _emit(RunEvent(
                event_type=EventType.AGENT_NARRATIVE,
                data={
                    "agent_id": step.agent,
                    "step_num": step.step,
                    "iteration_num": state["iteration_count"],
                    "rework_seq": _current_gate_rework_count(state, step),
                    "message": formatted,
                },
            ))
        else:
            print(f"\n[{step.agent}] Step {step.step} ({resolved_report_name or resolved_output_type})")

        reporting_events = parse_reporting_events(narrative)
        for event in reporting_events:
            logger.debug(
                "[Reporting] %s: %s — %s",
                event.get("agent_id"),
                event.get("event_type"),
                event.get("message", "")[:80],
            )

        validation_result: str | None = None
        structural_issues: list[str] = []
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

            # Adversarial mandate check (warning only, does not override result)
            enforce_adversarial_mandate(validation_result, report_dict)

            verdict_symbol = {"pass": "PASS", "warning": "WARNING", "fail": "FAIL"}.get(
                validation_result, validation_result
            )
            print(f"[{step.agent}] Verdict: {verdict_symbol}")

            # Emit validation result event directly
            _emit(RunEvent(
                event_type=EventType.VALIDATION_RESULT,
                data={
                    "result": validation_result,
                    "agent_id": step.agent,
                    "step_num": step.step,
                    "iteration_num": state["iteration_count"],
                    "rework_seq": _current_gate_rework_count(state, step),
                    "message": f"[{step.agent}] Verdict: {verdict_symbol}",
                },
            ))

            # Emit rework trigger event when validation fails and rework target exists
            if validation_result == "fail" and step.on_fail:
                rework_seq = _current_gate_rework_count(state, step) + 1
                _emit(RunEvent(
                    event_type=EventType.REWORK_TRIGGERED,
                    data={
                        "validator_step": step.step,
                        "rework_target": step.on_fail,
                        "rework_seq": rework_seq,
                        "iteration_num": state["iteration_count"],
                        "validation_result": validation_result,
                        "message": (
                            f"[{step.agent}] Rework triggered → {step.on_fail} "
                            f"(rework #{rework_seq})"
                        ),
                    },
                ))
        elif resolved_output_mode == "yaml_artifact":
            parsed_artifact = parse_artifact_checked(response.text, strict=True)
            if not parsed_artifact["valid"]:
                structural_issues = [parsed_artifact["error"]]
                artifact_yaml = ""
                _emit(RunEvent(
                    event_type=EventType.PIPELINE_WARNING,
                    data={
                        "agent_id": step.agent,
                        "step_num": step.step,
                        "iteration_num": state["iteration_count"],
                        "message": f"[{step.agent}] Output rejected by structural validation: {parsed_artifact['error']}",
                    },
                ))

        step_result = StepResult(
            step_id=step_node_id,
            agent_id=step.agent,
            artifact_yaml=artifact_yaml,
            artifact_type=resolved_report_name or resolved_output_type,
            model_used=response.model,
            validation_result=validation_result,
            narrative=narrative,
            reporting_events=reporting_events,
            # LLM usage tracking
            provider=response.provider,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cache_read_tokens=response.cache_read_tokens,
            cache_creation_tokens=response.cache_creation_tokens,
            # Timing
            started_at=started_at,
            finished_at=finished_at,
            # Position
            step_num=step.step,
            iteration_num=state["iteration_count"],
            rework_seq=_current_gate_rework_count(state, step),
        )
        if structural_issues:
            step_result["structural_issues"] = structural_issues
        if report_body:
            step_result["report_body"] = report_body

        # Emit STEP_COMPLETED event directly to EventBus
        step_completed_data = {
            "step_num": step.step,
            "agent_id": step.agent,
            "iteration_num": state["iteration_count"],
            "output_artifact": resolved_report_name or resolved_output_type,
            "model_used": response.model,
            "provider": response.provider,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cache_read_tokens": response.cache_read_tokens,
            "cache_creation_tokens": response.cache_creation_tokens,
            "validation_result": validation_result,
            "mode": step.mode,
            "rework_seq": _current_gate_rework_count(state, step),
            "started_at": started_at,
            "finished_at": finished_at,
            "message": f"[{step.agent}] Step {step.step} completed",
        }
        if report_body:
            step_completed_data["report_body"] = report_body

        _emit(RunEvent(
            event_type=EventType.STEP_COMPLETED,
            data=step_completed_data,
        ))

        # Persist artifact to disk immediately (crash-safe)
        saver = get_artifact_saver()
        if saver and (artifact_yaml or report_body is not None):
            saver(
                state["iteration_count"],
                step.agent,
                resolved_report_name or resolved_output_type,
                artifact_yaml if artifact_yaml else None,
                report_body if report_body else None,
                code_blocks,
            )

        new_latest = {**state["latest_artifacts"]}
        if artifact_yaml:
            new_latest[resolved_output_type] = artifact_yaml
        new_steps = [*state["steps_completed"], step_result]

        # Update code blocks context for downstream agents (PMAgent, TestAgent)
        new_code_blocks = {**state.get("latest_code_blocks", {})}
        if code_blocks:
            prev_context = new_code_blocks.get(step.agent, "")
            merged_context = merge_code_blocks(prev_context, code_blocks)
            new_code_blocks[step.agent] = merged_context

        new_rework_counts = {**state.get("rework_counts", {})}
        if step.agent == "ValidatorAgent":
            gate_key = step.step
            current_gate_count = new_rework_counts.get(gate_key, 0)
            if validation_result == "fail":
                new_rework_counts[gate_key] = current_gate_count + 1
            elif validation_result == "warning":
                new_rework_counts[gate_key] = current_gate_count
            else:
                new_rework_counts[gate_key] = 0

        state_update: dict = {
            "steps_completed": new_steps,
            "latest_artifacts": new_latest,
            "latest_code_blocks": new_code_blocks,
            "rework_counts": new_rework_counts,
        }
        if step.agent == "ValidatorAgent":
            state_update["latest_validation_result"] = validation_result or ""
            if validation_result == "warning":
                state_update["termination_reason"] = "warning_gate"
                state_update["termination_source_step"] = step.step
                state_update["termination_source_agent"] = step.agent
                # Arbiter context: 어떤 agent로 rework/upstream 할지 기록
                state_update["pm_arbiter_source_gate"] = step.step
                state_update["termination_rework_target"] = step.on_fail or ""
                state_update["termination_upstream_target"] = step.upstream_agent or step.on_fail or ""
            elif validation_result == "fail" and new_rework_counts.get(step.step, 0) >= state["max_reworks_per_gate"]:
                state_update["termination_reason"] = "max_reworks_exceeded"
                state_update["termination_source_step"] = step.step
                state_update["termination_source_agent"] = step.agent
                # Arbiter context
                state_update["pm_arbiter_source_gate"] = step.step
                state_update["termination_rework_target"] = step.on_fail or ""
                state_update["termination_upstream_target"] = step.upstream_agent or step.on_fail or ""

        # PMAgent iteration decision extraction
        if step.agent == "PMAgent":
            full_text = response.text
            
            # Step 1 (Initializer) extracts action type (new vs modify)
            if step.user_message_strategy == "pm_initializer":
                action_type = _extract_pm_action_type(full_text)
                state_update["pm_action_type"] = action_type
                print(f"[{step.agent}] Action 판정: {action_type.upper()}")

            # Assessment step extracts iteration decision
            if step.on_next_iteration:
                pm_decision = _extract_pm_decision(full_text)
                score = _extract_satisfaction_score(full_text)
                decision_label = {"continue": "CONTINUE (다음 iteration)", "done": "DONE (완료)"}.get(
                    pm_decision, pm_decision
                )
                print(f"[{step.agent}] Iteration 판정: {decision_label} (만족도: {score}/100)")
                step_result["satisfaction_score"] = score
                state_update["pm_decision"] = pm_decision

                # Increment iteration_count when continuing
                if pm_decision == "continue":
                    state_update["iteration_count"] = state["iteration_count"] + 1
                    state_update["rework_counts"] = {}
                    state_update["termination_reason"] = "normal"
                    state_update["termination_source_step"] = None
                    state_update["termination_source_agent"] = ""
                    state_update["latest_validation_result"] = ""

        return state_update

    node_fn.__name__ = step_node_id
    return node_fn


# ---------------------------------------------------------------------------
# PMAgent Arbiter node — 새 정규식
# ---------------------------------------------------------------------------

_PM_ARBITER_ACTION_RE = re.compile(
    r"ARBITER[_\s-]*ACTION\s*[:=\-]\s*[\"']?"
    r"(retry_producer|retry_upstream|restart_iteration|end_iteration)"
    r"[\"']?",
    re.IGNORECASE,
)


def _extract_arbiter_action(text: str) -> str:
    """Extract ARBITER_ACTION from PMAgent arbiter output.

    Returns one of: retry_producer, retry_upstream, restart_iteration, end_iteration.
    Defaults to 'end_iteration' if not found.
    """
    m = _PM_ARBITER_ACTION_RE.search(text)
    if m:
        return m.group(1).lower()

    cleaned = _strip_markdown_noise(text)
    m = _PM_ARBITER_ACTION_RE.search(cleaned)
    if m:
        return m.group(1).lower()

    logger.warning("[PMAgent Arbiter] ARBITER_ACTION not found — defaulting to 'end_iteration'")
    return "end_iteration"


def create_arbiter_node(
    step: StepDefinition,
    possible_targets: dict[str, str],
) -> Callable[[PipelineState], dict]:
    """Factory: create PMAgent arbiter LangGraph node.

    The arbiter receives context about why a validator gate escalated
    (warning or max_retries_exceeded), calls LLM to decide the routing
    action, and writes the target node_id to state for the downstream
    router to pick up.

    Args:
        step: StepDefinition for the arbiter (virtual step).
        possible_targets: dict of node_id → node_id for all valid routing targets.
    """
    agent_config = get_agent("PMAgent")
    system_prompt = build_system_prompt(agent_config, step)

    def arbiter_fn(state: PipelineState) -> dict:
        cancel = get_cancel_event()
        if cancel is not None and cancel.is_set():
            raise InterruptedError("Run cancelled before PMAgent arbiter")

        user_message = build_user_message(agent_config, step, state)

        _emit(RunEvent(
            event_type=EventType.STEP_STARTED,
            data={
                "step_num": 99,
                "agent_id": "PMAgent",
                "iteration_num": state["iteration_count"],
                "rework_seq": 0,
                "input_artifacts": [],
                "expected_output": "arbiter_decision",
                "mode": "arbiter",
                "message": "[PMAgent] Arbiter step started",
            },
        ))

        started_at = time.time()
        response = call_llm(
            system=system_prompt,
            user_message=user_message,
            model=step.model,
            max_tokens=step.max_tokens,
            min_response_chars=500,
        )
        finished_at = time.time()

        narrative = response.text.strip()
        action = _extract_arbiter_action(narrative)

        # 결정된 action을 target node_id로 매핑
        target_node: str = ""

        if action == "end_iteration":
            # pm_assessment_node를 찾는다 — possible_targets에서 PMAgent가 포함된 것
            for node_id in possible_targets:
                if "PMAgent" in node_id and node_id != "pm_arbiter":
                    target_node = node_id
                    break
            if not target_node:
                target_node = "__end__"

        elif action == "restart_iteration":
            # iteration 시작 node (보통 step_2_ReqAgent)
            # possible_targets에서 step 번호가 가장 작은 non-PMAgent 찾기
            import re as _re
            candidates = []
            for node_id in possible_targets:
                m = _re.match(r"step_(\d+)_(.+)", node_id)
                if m and "PMAgent" not in m.group(2):
                    candidates.append((int(m.group(1)), node_id))
            if candidates:
                candidates.sort()
                target_node = candidates[0][1]

        elif action == "retry_producer":
            # termination_source_step의 on_fail agent를 state에서 가져온다
            target_agent = state.get("termination_rework_target", "")
            for node_id in possible_targets:
                if target_agent and target_agent in node_id:
                    target_node = node_id
                    break

        elif action == "retry_upstream":
            target_agent = state.get("termination_upstream_target", "")
            for node_id in possible_targets:
                if target_agent and target_agent in node_id:
                    target_node = node_id
                    break
            # upstream이 없으면 producer로 fallback
            if not target_node:
                target_agent = state.get("termination_rework_target", "")
                for node_id in possible_targets:
                    if target_agent and target_agent in node_id:
                        target_node = node_id
                        break

        if not target_node:
            logger.warning(
                "[PMAgent Arbiter] Could not resolve target for action=%s — falling back to __end__",
                action,
            )
            target_node = "__end__"

        formatted = _format_narrative(narrative, "PMAgent")
        print(f"\n{formatted}")
        print(f"[PMAgent] Arbiter 판정: {action.upper()} → {target_node}")

        _emit(RunEvent(
            event_type=EventType.AGENT_NARRATIVE,
            data={
                "agent_id": "PMAgent",
                "step_num": 99,
                "iteration_num": state["iteration_count"],
                "rework_seq": 0,
                "message": formatted,
            },
        ))

        _emit(RunEvent(
            event_type=EventType.STEP_COMPLETED,
            data={
                "step_num": 99,
                "agent_id": "PMAgent",
                "iteration_num": state["iteration_count"],
                "output_artifact": "arbiter_decision",
                "model_used": response.model,
                "provider": response.provider,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cache_read_tokens": response.cache_read_tokens,
                "cache_creation_tokens": response.cache_creation_tokens,
                "validation_result": None,
                "mode": "arbiter",
                "rework_seq": 0,
                "started_at": started_at,
                "finished_at": finished_at,
                "message": f"[PMAgent] Arbiter step completed: {action}",
            },
        ))

        # rework_counts 리셋 (retry 시 새로운 시도로 취급)
        new_rework_counts = {**state.get("rework_counts", {})}
        if action in ("retry_producer", "retry_upstream", "restart_iteration"):
            if action == "restart_iteration":
                new_rework_counts = {}  # 전체 리셋
            else:
                # 해당 gate의 rework count만 리셋
                source_gate = state.get("pm_arbiter_source_gate", 0)
                if source_gate in new_rework_counts:
                    new_rework_counts[source_gate] = 0

        return {
            "pm_arbiter_action": action,
            "pm_arbiter_target_node": target_node,
            "rework_counts": new_rework_counts,
            "termination_reason": "normal",  # arbiter가 판단했으므로 리셋
            "termination_source_step": None,
            "termination_source_agent": "",
        }

    arbiter_fn.__name__ = "pm_arbiter"
    return arbiter_fn
