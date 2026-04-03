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
    pm_assessment_node: str | None = None

    for step_def in steps:
        node_id = f"step_{step_def.step}_{step_def.agent}"
        node_ids[step_def.step] = node_id
        if step_def.agent not in agent_to_node:
            agent_to_node[step_def.agent] = node_id
        if step_def.agent == "PMAgent" and step_def.on_next_iteration:
            pm_assessment_node = node_id

        node_fn = create_agent_node(step_def)
        graph.add_node(node_id, node_fn)

    # Arbiter 노드: warning/max_retries 시 PMAgent가 라우팅 판단
    # __arbiter__를 사용하는 gate가 하나라도 있으면 생성
    arbiter_gates = [
        s for s in steps
        if s.agent == "ValidatorAgent"
        and (s.on_warning == "__arbiter__" or s.on_max_retries == "__arbiter__")
    ]
    arbiter_node_id: str | None = None
    arbiter_possible_targets: dict[str, str] = {}  # node_id → node_id (edge key → target)

    # gate_step_num → pass target node_id (accept_and_continue용)
    gate_pass_targets: dict[int, str] = {}

    if arbiter_gates:
        from app.core.executor.generic_agent import create_arbiter_node

        # iteration 시작 agent (PMAgent 다음 첫 번째 non-PM agent)
        iteration_start_node = None
        for s in steps:
            if s.agent != "PMAgent":
                iteration_start_node = node_ids[s.step]
                break

        # 각 gate별 가능한 target 수집
        for gate_step in arbiter_gates:
            producer_node = agent_to_node.get(gate_step.on_fail)
            if producer_node:
                arbiter_possible_targets[producer_node] = producer_node
            if gate_step.upstream_agent:
                upstream_node = agent_to_node.get(gate_step.upstream_agent)
                if upstream_node:
                    arbiter_possible_targets[upstream_node] = upstream_node

            # accept_and_continue용: 각 gate의 pass target (다음 step) 수집
            gate_idx = next(
                (i for i, s in enumerate(steps) if s.step == gate_step.step), None
            )
            if gate_idx is not None and gate_idx < len(steps) - 1:
                pass_node = node_ids[steps[gate_idx + 1].step]
                gate_pass_targets[gate_step.step] = pass_node
                arbiter_possible_targets[pass_node] = pass_node

        if iteration_start_node:
            arbiter_possible_targets[iteration_start_node] = iteration_start_node
        if pm_assessment_node:
            arbiter_possible_targets[pm_assessment_node] = pm_assessment_node

        arbiter_step = StepDefinition(
            step=99,  # 가상 step 번호 (pipeline YAML에 없음)
            agent="PMAgent",
            model=steps[0].model,  # 첫 번째 step의 모델 사용
            output_mode="narrative_only",
            user_message_strategy="pm_arbiter",
        )
        arbiter_node_id = "pm_arbiter"
        arbiter_node_fn = create_arbiter_node(
            arbiter_step, arbiter_possible_targets, gate_pass_targets
        )
        graph.add_node(arbiter_node_id, arbiter_node_fn)

    first_node = node_ids[steps[0].step]
    graph.set_entry_point(first_node)

    # Arbiter의 conditional edges 등록
    if arbiter_node_id and arbiter_possible_targets:
        from app.core.pipeline.routing import make_arbiter_router

        arbiter_routing_fn = make_arbiter_router()
        # edge key = target node_id, value = target node_id
        arbiter_edges = dict(arbiter_possible_targets)
        arbiter_edges["__end__"] = END  # fallback: end_iteration이 assessment 없이 종료할 때
        graph.add_conditional_edges(arbiter_node_id, arbiter_routing_fn, arbiter_edges)

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

            # warning 라우팅 대상 결정
            if step_def.on_warning == "__arbiter__" and arbiter_node_id:
                warning_target = arbiter_node_id
            elif not step_def.on_warning:
                warning_target = pm_assessment_node
            elif step_def.on_warning == "PMAgent" and pm_assessment_node is not None:
                warning_target = pm_assessment_node
            else:
                warning_target = agent_to_node.get(step_def.on_warning)

            # force_pass (max_retries 초과) 라우팅 대상 결정
            if step_def.on_max_retries == "__arbiter__" and arbiter_node_id:
                force_pass_target = arbiter_node_id
            else:
                force_pass_target = pass_target

            routing_fn = make_validator_router(step_num=step_def.step)

            edges = {
                "pass": pass_target,
                "rework": rework_target,
                "force_pass": force_pass_target,
            }
            if warning_target is not None:
                edges["warning"] = warning_target
            graph.add_conditional_edges(current_node, routing_fn, edges)
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
    workspace_root = ""
    workspace_root_name = ""
    workspace_mode = "internal_run_workspace"
    if workspace_path:
        workspace_root_path = Path(workspace_path).resolve()
        workspace_context = scan_workspace(workspace_root_path)
        workspace_root = str(workspace_root_path)
        workspace_root_name = workspace_root_path.name
        workspace_mode = "external_project_root"

    initial_state: PipelineState = {
        "user_story": user_story,
        "steps_completed": [],
        "latest_artifacts": {},
        "current_step_index": 0,
        "iteration_count": 1,
        "max_iterations": pipeline_def.max_iterations,
        "rework_counts": {},
        "max_reworks_per_gate": pipeline_def.max_reworks_per_gate,
        "pipeline_status": "running",
        "pm_decision": "",
        "pm_action_type": "",
        "latest_code_blocks": {},
        "workspace_context": workspace_context,
        "workspace_root": workspace_root,
        "workspace_root_name": workspace_root_name,
        "workspace_mode": workspace_mode,
        "termination_reason": "normal",
        "termination_source_step": None,
        "termination_source_agent": "",
        "latest_validation_result": "",
        # Arbiter 관련 초기값
        "pm_arbiter_action": "",
        "pm_arbiter_target_node": "",
        "pm_arbiter_source_gate": 0,
        "termination_rework_target": "",
        "termination_upstream_target": "",
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
    restored_state["rework_counts"] = {}
    restored_state["pm_decision"] = ""
    restored_state["latest_code_blocks"] = {}
    restored_state["max_iterations"] = pipeline_def.max_iterations
    restored_state["max_reworks_per_gate"] = pipeline_def.max_reworks_per_gate
    restored_state["pipeline_status"] = "running"
    restored_state.setdefault("workspace_root", "")
    restored_state.setdefault("workspace_root_name", "")
    restored_state.setdefault("workspace_mode", "internal_run_workspace")
    restored_state["termination_reason"] = "normal"
    restored_state["termination_source_step"] = None
    restored_state["termination_source_agent"] = ""
    restored_state["latest_validation_result"] = ""
    restored_state.setdefault("pm_arbiter_action", "")
    restored_state.setdefault("pm_arbiter_target_node", "")
    restored_state.setdefault("pm_arbiter_source_gate", 0)
    restored_state.setdefault("termination_rework_target", "")
    restored_state.setdefault("termination_upstream_target", "")

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

    rework_counts = final_state.get("rework_counts", {})
    if any(v >= pipeline_def.max_reworks_per_gate for v in rework_counts.values()):
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
