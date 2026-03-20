"""Dynamic graph builder — constructs LangGraph from PipelineDefinition."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from langgraph.graph import StateGraph, END

from registry.models import PipelineDefinition, StepDefinition
from pipeline.state import PipelineState
from pipeline.routing import make_validator_router
from executor.generic_agent import create_agent_node
from llm_client import QuotaExhaustedError


logger = logging.getLogger(__name__)


def load_pipeline_definition(path: str | Path) -> PipelineDefinition:
    """Load a PipelineDefinition from a YAML file."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PipelineDefinition(**raw)


def build_graph_from_definition(pipeline_def: PipelineDefinition) -> StateGraph:
    """Build a LangGraph StateGraph from a PipelineDefinition.

    - Each step becomes a named node: "step_{N}_{AgentId}"
    - Non-validator steps get a simple edge to the next step
    - Validator steps with on_fail get conditional edges:
        pass → next step, rework → on_fail target, max_retries → END
    """
    graph = StateGraph(PipelineState)
    steps = pipeline_def.steps

    # Build node ID mappings
    node_ids: dict[int, str] = {}          # step number → node ID
    agent_to_node: dict[str, str] = {}     # agent_id → FIRST node ID for that agent

    for step_def in steps:
        node_id = f"step_{step_def.step}_{step_def.agent}"
        node_ids[step_def.step] = node_id
        if step_def.agent not in agent_to_node:
            agent_to_node[step_def.agent] = node_id

        # Create and register node
        node_fn = create_agent_node(step_def)
        graph.add_node(node_id, node_fn)

    # Set entry point
    first_node = node_ids[steps[0].step]
    graph.set_entry_point(first_node)

    # Wire edges
    for i, step_def in enumerate(steps):
        current_node = node_ids[step_def.step]
        is_last = i == len(steps) - 1
        next_node = node_ids[steps[i + 1].step] if not is_last else None

        if step_def.agent == "ValidatorAgent" and step_def.on_fail:
            # Conditional edge for validation gates
            rework_target = agent_to_node.get(step_def.on_fail)
            if rework_target is None:
                raise ValueError(
                    f"Step {step_def.step}: on_fail references '{step_def.on_fail}' "
                    f"but no step uses that agent. "
                    f"Available agents: {list(agent_to_node.keys())}"
                )

            pass_target = next_node if next_node else END
            routing_fn = make_validator_router(
                step_num=step_def.step,
                max_iterations=pipeline_def.max_iterations,
            )

            graph.add_conditional_edges(
                current_node,
                routing_fn,
                {
                    "pass": pass_target,
                    "rework": rework_target,
                    "max_retries": END,
                },
            )
        else:
            # Simple edge to next step or END
            target = next_node if next_node else END
            graph.add_edge(current_node, target)

    return graph


def create_pipeline(pipeline_def: PipelineDefinition):
    """Build and compile a runnable pipeline from a definition."""
    graph = build_graph_from_definition(pipeline_def)
    return graph.compile()


def run_pipeline(
    pipeline_def: PipelineDefinition,
    user_story: str,
) -> PipelineState:
    """Execute a dynamic pipeline end-to-end."""
    initial_state: PipelineState = {
        "user_story": user_story,
        "steps_completed": [],
        "latest_artifacts": {},
        "current_step_index": 0,
        "iteration_count": 0,
        "max_iterations": pipeline_def.max_iterations,
        "pipeline_status": "running",
    }

    print("\n" + "=" * 60)
    print(f"[Pipeline] '{pipeline_def.name}' 시작")
    print(f"[Pipeline] User Story: {user_story[:100]}...")
    print(f"[Pipeline] Steps: {len(pipeline_def.steps)}, Max iterations: {pipeline_def.max_iterations}")
    agents_summary = " → ".join(
        f"{s.agent}{'(' + s.mode + ')' if s.mode else ''}" for s in pipeline_def.steps
    )
    print(f"[Pipeline] Flow: {agents_summary}")
    print("=" * 60)

    compiled = create_pipeline(pipeline_def)
 
    try:
        final_state = compiled.invoke(initial_state)
    except QuotaExhaustedError as exc:
        print("\n" + "=" * 60)
        print(f"[Pipeline] QUOTA EXHAUSTED — 파이프라인 중단")
        print(f"[Pipeline] {exc}")
        print("=" * 60)
        # Return partial state so artifacts generated so far can be saved
        initial_state["pipeline_status"] = "quota_exhausted"
        return initial_state
    except Exception as exc:
        print("\n" + "=" * 60)
        print(f"[Pipeline] ERROR — 파이프라인 비정상 중단: {type(exc).__name__}: {exc}")
        print("=" * 60)
        initial_state["pipeline_status"] = f"error: {type(exc).__name__}"
        return initial_state
    
    # Determine final status
    last_validation = None
    for sr in reversed(final_state["steps_completed"]):
        if sr["validation_result"] is not None:
            last_validation = sr["validation_result"]
            break

    if final_state["iteration_count"] >= pipeline_def.max_iterations:
        final_state["pipeline_status"] = "max_retries_exceeded"
    else:
        final_state["pipeline_status"] = "completed"

    print("\n" + "=" * 60)
    print(f"[Pipeline] '{pipeline_def.name}' 완료")
    print(f"[Pipeline] Status: {final_state['pipeline_status']}")
    print(f"[Pipeline] Steps executed: {len(final_state['steps_completed'])}")
    print(f"[Pipeline] Iterations used: {final_state['iteration_count']}")
    if final_state["latest_artifacts"]:
        print(f"[Pipeline] Artifacts: {list(final_state['latest_artifacts'].keys())}")
    print("=" * 60)

    return final_state
