"""Dynamic graph builder — constructs LangGraph from PipelineDefinition."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from langgraph.graph import StateGraph, END

from app.core.registry.models import PipelineDefinition, StepDefinition
from app.core.pipeline.state import PipelineState
from app.core.pipeline.routing import make_validator_router, make_pm_iteration_router
from app.core.executor.generic_agent import create_agent_node
from app.core.llm_client import QuotaExhaustedError

logger = logging.getLogger(__name__)


def load_pipeline_definition(path: str | Path) -> PipelineDefinition:
    """Load a PipelineDefinition from a YAML file."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PipelineDefinition(**raw)


def build_graph_from_definition(pipeline_def: PipelineDefinition) -> StateGraph:
    """Build a LangGraph StateGraph from a PipelineDefinition."""
    graph = StateGraph(PipelineState)
    steps = pipeline_def.steps

    node_ids: dict[int, str] = {}
    agent_to_node: dict[str, str] = {}

    for step_def in steps:
        node_id = f"step_{step_def.step}_{step_def.agent}"
        node_ids[step_def.step] = node_id
        if step_def.agent not in agent_to_node:
            agent_to_node[step_def.agent] = node_id

        node_fn = create_agent_node(step_def)
        graph.add_node(node_id, node_fn)

    first_node = node_ids[steps[0].step]
    graph.set_entry_point(first_node)

    for i, step_def in enumerate(steps):
        current_node = node_ids[step_def.step]
        is_last = i == len(steps) - 1
        next_node = node_ids[steps[i + 1].step] if not is_last else None

        if step_def.agent == "ValidatorAgent" and step_def.on_fail:
            # ValidatorAgent: pass/fail conditional routing
            rework_target = agent_to_node.get(step_def.on_fail)
            if rework_target is None:
                raise ValueError(
                    f"Step {step_def.step}: on_fail references '{step_def.on_fail}' "
                    f"but no step uses that agent. "
                    f"Available agents: {list(agent_to_node.keys())}"
                )

            pass_target = next_node if next_node else END
            routing_fn = make_validator_router(step_num=step_def.step)

            graph.add_conditional_edges(
                current_node,
                routing_fn,
                {
                    "pass": pass_target,
                    "rework": rework_target,
                    "max_retries": END,
                },
            )
        elif step_def.on_next_iteration:
            # PMAgent: iteration decision conditional routing
            iteration_target = agent_to_node.get(step_def.on_next_iteration)
            if iteration_target is None:
                raise ValueError(
                    f"Step {step_def.step}: on_next_iteration references "
                    f"'{step_def.on_next_iteration}' but no step uses that agent. "
                    f"Available agents: {list(agent_to_node.keys())}"
                )

            routing_fn = make_pm_iteration_router(step_num=step_def.step)

            graph.add_conditional_edges(
                current_node,
                routing_fn,
                {
                    "next_iteration": iteration_target,
                    "done": END,
                    "max_iterations": END,
                },
            )
        else:
            target = next_node if next_node else END
            graph.add_edge(current_node, target)

    return graph


def create_pipeline(pipeline_def: PipelineDefinition):
    """Build and compile a runnable pipeline from a definition."""
    graph = build_graph_from_definition(pipeline_def)
    return graph.compile()


from app.core.artifacts.workspace_scanner import scan_workspace


def run_pipeline(
    pipeline_def: PipelineDefinition,
    user_story: str,
    workspace_path: str | Path | None = None,
) -> PipelineState:
    """Execute a dynamic pipeline end-to-end."""
    workspace_context = {}
    if workspace_path:
        workspace_context = scan_workspace(workspace_path)

    initial_state: PipelineState = {
        "user_story": user_story,
        "steps_completed": [],
        "latest_artifacts": {},
        "current_step_index": 0,
        "iteration_count": 1,
        "max_iterations": pipeline_def.max_iterations,
        "rework_count": 0,
        "max_reworks_per_gate": pipeline_def.max_reworks_per_gate,
        "pipeline_status": "running",
        "pm_decision": "",
        "pm_action_type": "",
        "latest_code_blocks": {},
        "workspace_context": workspace_context,
    }

    return _execute_pipeline(pipeline_def, initial_state)


def resume_pipeline(
    pipeline_def: PipelineDefinition,
    restored_state: PipelineState,
) -> PipelineState:
    """Resume a previously interrupted pipeline from restored state.

    Completed steps are placed in a thread-local replay queue.  When
    LangGraph re-executes the graph from the entry point, each node checks
    the queue: if the front matches, the step result is replayed without an
    LLM call.  Once the queue is exhausted (or a mismatch is detected),
    normal execution resumes from that point.
    """
    from app.core.executor.generic_agent import set_replay_queue, clear_replay_queue

    # Populate replay queue, then reset state to initial values so the graph
    # traversal reproduces the same node/routing sequence as the original run.
    set_replay_queue(restored_state["steps_completed"])

    restored_state["steps_completed"] = []
    restored_state["latest_artifacts"] = {}
    restored_state["iteration_count"] = 1
    restored_state["rework_count"] = 0
    restored_state["pm_decision"] = ""
    restored_state["latest_code_blocks"] = {}
    restored_state["max_iterations"] = pipeline_def.max_iterations
    restored_state["max_reworks_per_gate"] = pipeline_def.max_reworks_per_gate
    restored_state["pipeline_status"] = "running"

    try:
        return _execute_pipeline(pipeline_def, restored_state, is_resume=True)
    finally:
        clear_replay_queue()


def _execute_pipeline(
    pipeline_def: PipelineDefinition,
    initial_state: PipelineState,
    is_resume: bool = False,
) -> PipelineState:
    """Internal: compile and execute a pipeline with the given initial state."""
    mode_label = "재개(Resume)" if is_resume else "시작"

    print("\n" + "=" * 60)
    print(f"[Pipeline] '{pipeline_def.name}' {mode_label}")
    print(f"[Pipeline] User Story: {initial_state['user_story'][:100]}...")
    if is_resume:
        print(f"[Pipeline] Resuming from iteration={initial_state['iteration_count']}, "
              f"steps_completed={len(initial_state['steps_completed'])}")
    print(f"[Pipeline] Steps: {len(pipeline_def.steps)}, "
          f"Max spiral iterations: {pipeline_def.max_iterations}, "
          f"Max reworks/gate: {pipeline_def.max_reworks_per_gate}")
    agents_summary = " → ".join(
        f"{s.agent}{'(' + s.mode + ')' if s.mode else ''}" for s in pipeline_def.steps
    )
    print(f"[Pipeline] Flow: {agents_summary}")
    print("=" * 60)

    compiled = create_pipeline(pipeline_def)

    try:
        final_state: PipelineState = compiled.invoke(initial_state)  # type: ignore[assignment]
    except QuotaExhaustedError as exc:
        print("\n" + "=" * 60)
        print("[Pipeline] QUOTA EXHAUSTED — 파이프라인 중단")
        print(f"[Pipeline] {exc}")
        print("=" * 60)
        initial_state["pipeline_status"] = "quota_exhausted"
        return initial_state
    except Exception as exc:
        print("\n" + "=" * 60)
        print(f"[Pipeline] ERROR — 파이프라인 비정상 중단: {type(exc).__name__}: {exc}")
        print("=" * 60)
        initial_state["pipeline_status"] = f"error: {type(exc).__name__}"
        return initial_state

    if final_state["rework_count"] >= pipeline_def.max_reworks_per_gate:
        final_state["pipeline_status"] = "max_reworks_exceeded"
    else:
        final_state["pipeline_status"] = "completed"

    total_reworks = sum(
        1 for sr in final_state["steps_completed"]
        if sr["validation_result"] in ("fail", "warning")
    )

    print("\n" + "=" * 60)
    print(f"[Pipeline] '{pipeline_def.name}' 완료")
    print(f"[Pipeline] Status: {final_state['pipeline_status']}")
    print(f"[Pipeline] Spiral iteration: {final_state['iteration_count']}")
    print(f"[Pipeline] Steps executed: {len(final_state['steps_completed'])}")
    print(f"[Pipeline] Total reworks: {total_reworks}")
    if final_state["latest_artifacts"]:
        print(f"[Pipeline] Artifacts: {list(final_state['latest_artifacts'].keys())}")
    print("=" * 60)

    return final_state
