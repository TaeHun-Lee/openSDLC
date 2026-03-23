"""User message build strategies for each agent type."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.registry.models import AgentConfig, StepDefinition
    from app.core.pipeline.state import PipelineState


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
        if input_name in latest and latest[input_name]:
            parts.append(f"{input_name}:\n{latest[input_name]}\n")
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


def _strategy_pm_initializer(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    """PMAgent Step 1: project initialization only.

    Receives only the user story. PMAgent sets project scope and passes
    control to the next agent — no iteration assessment, no artifact generation.
    """
    return (
        "아래 User Story를 접수하라.\n"
        "너의 역할은 프로젝트 초기화(Project Initialization)이다.\n\n"
        "수행할 작업:\n"
        "1. User Story를 분석하여 프로젝트 범위(scope)를 파악하라.\n"
        "2. 프로젝트 개요를 간단히 정리하라 (3-5문장 이내).\n"
        "3. 다음 단계(ReqAgent)에 전달할 핵심 요구사항을 요약하라.\n\n"
        "금지사항:\n"
        "- iteration_assessment를 작성하지 마라.\n"
        "- ITERATION_DECISION 판정을 내리지 마라.\n"
        "- 코드를 생성하거나 구현하지 마라.\n"
        "- 테스트를 설계하거나 실행하지 마라.\n"
        "- 사용자 승인을 요청하지 마라. 자율적으로 판단하고 진행하라.\n\n"
        f"User Story:\n{state['user_story']}"
    )


def _strategy_pm_assessor(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    """PMAgent iteration assessment: receives all artifacts including code implementation.

    PMAgent must directly analyze the code in ImplementationArtifact.code_files
    and make a structured iteration decision.
    """
    latest = state["latest_artifacts"]
    iteration = state["iteration_count"]

    parts = [
        f"현재 Iteration {iteration}의 전체 산출물을 분석하여 "
        f"iteration_assessment를 작성하고 다음 iteration 실행 여부를 판정하라.\n",
        f"원본 User Story:\n{state['user_story']}\n",
    ]

    # Feed all available artifacts
    artifact_order = [
        "UseCaseModelArtifact",
        "TestDesignArtifact",
        "ImplementationArtifact",
        "TestReportArtifact",
        "FeedbackArtifact",
        "ValidationReportArtifact",
    ]
    for atype in artifact_order:
        content = latest.get(atype, "")
        if content:
            parts.append(f"--- {atype} ---\n{content}\n")

    # Also include any other artifacts not in the standard order
    for atype, content in latest.items():
        if atype not in artifact_order and content:
            parts.append(f"--- {atype} ---\n{content}\n")

    parts.append(
        "\n=== 판정 지침 ===\n"
        "위 ImplementationArtifact의 code_files 내 실제 코드를 직접 분석하라.\n"
        "다음 기준으로 구현 완성도를 평가하라:\n"
        "1. User Story의 모든 요구사항이 코드에 구현되어 있는가?\n"
        "2. UseCaseModelArtifact의 각 use case가 코드에 반영되어 있는가?\n"
        "3. TestReportArtifact에서 발견된 결함이 코드에서 실제로 존재하는가?\n"
        "4. 코드의 구조, 에러 처리, 엣지 케이스 대응이 적절한가?\n"
        "5. FeedbackArtifact의 개선 사항이 반영되었는가? (iteration 2+ 인 경우)\n"
        "\n"
        "assessment 마지막에 반드시 아래 형식의 판정 블록을 포함하라:\n"
        "```\n"
        "ITERATION_DECISION: continue\n"
        "DECISION_REASON: (판정 사유를 한 줄로 기술)\n"
        "SATISFACTION_SCORE: (0-100 점수)\n"
        "```\n"
        "또는\n"
        "```\n"
        "ITERATION_DECISION: done\n"
        "DECISION_REASON: (판정 사유를 한 줄로 기술)\n"
        "SATISFACTION_SCORE: (0-100 점수)\n"
        "```\n"
        "\n"
        "판정 기준:\n"
        "- SATISFACTION_SCORE < 90 → ITERATION_DECISION: continue\n"
        "- SATISFACTION_SCORE >= 90 이고 blocking fail 없음 → ITERATION_DECISION: done\n"
        "- ValidatorAgent fail이 해소되지 않았으면 반드시 continue\n"
    )

    return "\n".join(parts)


_STRATEGIES: dict[str, callable] = {
    "req_agent": _strategy_req_agent,
    "validator": _strategy_validator,
    "input_assembler": _strategy_input_assembler,
    "test_agent": _strategy_test_agent,
    "pm_initializer": _strategy_pm_initializer,
    "pm_assessor": _strategy_pm_assessor,
}


def build_user_message(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    """Build user message using the strategy specified in step or agent_config."""
    # Step-level override takes priority over agent config
    strategy_key = step.user_message_strategy or agent_config.user_message_strategy
    strategy_fn = _STRATEGIES.get(strategy_key)
    if strategy_fn is None:
        raise ValueError(
            f"Unknown user_message_strategy: {strategy_key!r}. "
            f"Available: {list(_STRATEGIES)}"
        )
    return strategy_fn(agent_config, step, state)
