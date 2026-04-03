"""User message build strategies for each agent type."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.prompts.loader import load_template

if TYPE_CHECKING:
    from app.core.registry.models import AgentConfig, StepDefinition
    from app.core.pipeline.state import PipelineState


def _build_schema_reminder(
    agent_config: AgentConfig,
    step: StepDefinition,
) -> str:
    """Append the output schema near the end of the user message."""
    artifact_outputs = [o for o in agent_config.primary_outputs if o.endswith("Artifact")]
    if not artifact_outputs:
        return ""

    if step.mode and len(artifact_outputs) > 1:
        if step.mode == "design":
            target = next((o for o in artifact_outputs if "Design" in o), artifact_outputs[0])
        elif step.mode == "execution":
            target = next((o for o in artifact_outputs if "Report" in o), artifact_outputs[-1])
        else:
            target = artifact_outputs[0]
    else:
        target = artifact_outputs[0]

    try:
        template_text = load_template(target)
    except FileNotFoundError:
        return ""

    id_rules = (
        "\n\nID 명명규칙:\n"
        "- artifact_id: 아티팩트 유형 약어 + 순번 (예: UC-01, TD-01, IMPL-01, TEST-01, FB-01, VAL-01)\n"
        "- rework 시 순번을 증가시킨다 (예: TD-01 → TD-02)\n"
        "- 하위 항목 ID는 상위 artifact_id를 접두사로 사용한다.\n"
        "- source_artifact_ids, test_scenario_ids 등 참조 필드는 실제 존재하는 ID만 사용하라.\n"
    )

    return (
        "\n\n=== 출력 스키마 준수 지침 ===\n"
        f"반드시 아래 {target} 템플릿의 스키마를 정확히 따라 YAML을 작성하라.\n"
        "- 모든 필수 필드를 빠짐없이 포함할 것.\n"
        "- `artifact_id` 필드를 반드시 첫 번째 줄에 포함할 것.\n"
        "- YAML 코드블록(```yaml ... ```)으로 감싸서 출력할 것.\n"
        f"{id_rules}\n"
        f"템플릿:\n```yaml\n{template_text}\n```"
    )


def _strategy_req_agent(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    latest = state["latest_artifacts"]
    workspace_context = state.get("workspace_context", {})
    action_type = state.get("pm_action_type", "new")
    
    is_retry = False
    if state["steps_completed"]:
        last_step = state["steps_completed"][-1]
        if last_step["agent_id"] == "ValidatorAgent" and last_step.get("validation_result") in ("fail", "warning"):
            is_retry = True

    if not is_retry:
        prompt = (
            "[PMAgent] 아래 User Story를 분석하여 UseCaseModelArtifact를 작성하라.\n\n"
            f"User Story:\n{state['user_story']}\n"
        )
        if action_type == "modify" and workspace_context:
            prompt += "\n--- 기존 작업 공간 파일 내용 (참고용) ---\n"
            for path, content in workspace_context.items():
                prompt += f"File: {path}\n```\n{content}\n```\n"
            prompt += "\n주의: 기존 소스 코드의 기술 스택, UI 구조, API 설계를 분석하여 요구사항을 정의하라."
        return prompt + _build_schema_reminder(agent_config, step)

    return (
        "[PMAgent] ValidatorAgent가 아래 사유로 이전 artifact를 반려하였다.\n"
        "ValidationReport의 지적 사항을 반영하여 UseCaseModelArtifact를 처음부터 완전히 새로 작성하라.\n"
        "이전 artifact를 복사하여 부분 수정하지 마라. 새 artifact를 독립적으로 생성하라.\n"
        "특히 ID 참조(artifact_id, use_case_ids 등)가 현재 참조 대상의 실제 ID와 정확히 일치하는지 확인하라.\n\n"
        f"ValidationReport:\n{latest.get('ValidationReportArtifact', '')}\n\n"
        f"이전 UC Artifact (참조용, 복사 금지):\n{latest.get('UseCaseModelArtifact', '')}\n\n"
        f"원본 User Story:\n{state['user_story']}"
    ) + _build_schema_reminder(agent_config, step)


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
    prompt = (
        f"아래 {target_type}를 검증하고 ValidationReportArtifact를 작성하라.\n"
        "이 artifact 외의 정보(이전 agent의 사고 과정 등)는 참조하지 말 것.\n\n"
        f"{target_type}:\n{target_yaml}"
    )
    
    # If validating ImplementationArtifact, also provide the code context
    if target_type.startswith("ImplementationArtifact"):
        code_context = state.get("latest_code_blocks", {}).get("CodeAgent", "")
        if code_context:
            prompt += f"\n\n--- 구현 소스코드 ---\n{code_context}\n"
            prompt += "\n주의: Search-Replace 프로토콜(SEARCH/REPLACE 마커)이 사용된 경우, 마커의 짝이 맞는지와 구문이 올바른지 반드시 확인하라."

    return prompt


def _strategy_input_assembler(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    """Generic strategy: assemble primary_inputs from latest artifacts."""
    latest = state["latest_artifacts"]
    action_type = state.get("pm_action_type", "new")
    workspace_context = state.get("workspace_context", {})
    workspace_root = state.get("workspace_root", "")
    workspace_root_name = state.get("workspace_root_name", "")
    workspace_mode = state.get("workspace_mode", "internal_run_workspace")
    output_name = agent_config.primary_outputs[0] if agent_config.primary_outputs else "artifact"
    
    is_retry = False
    if state["steps_completed"]:
        last_step = state["steps_completed"][-1]
        if last_step["agent_id"] == "ValidatorAgent" and last_step.get("validation_result") in ("fail", "warning"):
            is_retry = True

    parts = []
    if is_retry:
        parts.append(f"[PMAgent] ValidatorAgent가 아래 사유로 이전 {output_name}를 반려하였다.")
        parts.append(f"ValidationReport의 지적 사항을 반영하여 {output_name}를 처음부터 완전히 새로 작성하라.")
        parts.append("이전 artifact를 복사하여 부분 수정하지 마라. 새 artifact를 독립적으로 생성하라.")
        parts.append(
            "특히 ID 참조(artifact_id, source_artifact_ids, test_scenario_ids 등)가 현재 참조 대상의 실제 ID와 정확히 일치하는지 확인하라.\n"
        )
        parts.append(f"ValidationReport:\n{latest.get('ValidationReportArtifact', '')}\n")
        parts.append(f"이전 {output_name} (참조용, 복사 금지):\n{latest.get(output_name, '')}\n")
        parts.append("--- 참조 산출물 ---")
    else:
        parts.append(f"아래 승인된 artifacts를 기반으로 {output_name}를 작성하라.\n")
        if action_type == "modify":
            parts.append(f"주의: 이번 작업은 기존 코드를 수정하는 '{action_type}' 방식이다. 기존 파일 내용을 참고하여 필요한 부분만 수정하거나 추가하라.\n")

    for input_name in agent_config.primary_inputs:
        actual_key = input_name
        if input_name not in latest:
            for k in latest.keys():
                if input_name.startswith(k):
                    actual_key = k
                    break
                    
        # Don't duplicate ValidationReportArtifact if we already added it for rework
        if actual_key == "ValidationReportArtifact" and is_retry:
            continue
            
        if actual_key in latest and latest[actual_key]:
            parts.append(f"{input_name}:\n{latest[actual_key]}\n")
            
    if len(parts) == 1 and not is_retry:
        for atype, ayaml in latest.items():
            if ayaml:
                parts.append(f"{atype}:\n{ayaml}\n")

    # If in modify mode, inject existing workspace files as context for CodeAgent
    if step.agent == "CodeAgent" and action_type == "modify" and workspace_context:
        if workspace_mode == "external_project_root" and workspace_root:
            parts.append(
                "경로 규칙:\n"
                f"- 현재 작업의 파일 경로 기준은 external workspace root(`{workspace_root}`)이다.\n"
                "- 모든 files_changed 및 code block FILE path는 이 root 기준 상대경로만 사용하라.\n"
                "- 예: `server.js`, `package.json`, `src/index.ts`\n"
                f"- 금지: `{workspace_root_name}/server.js`, `workspace/{workspace_root_name}/server.js`, 절대경로\n"
            )
        parts.append("\n--- 기존 작업 공간 파일 내용 ---")
        for path, content in workspace_context.items():
            parts.append(f"File: {path}\n```\n{content}\n```\n")
                
    return "\n".join(parts) + _build_schema_reminder(agent_config, step)


def _strategy_test_agent(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    latest = state["latest_artifacts"]
    mode = step.mode or "design"
    output_name = "TestDesignArtifact" if mode == "design" else "TestReportArtifact"

    is_retry = False
    if state["steps_completed"]:
        last_step = state["steps_completed"][-1]
        if last_step["agent_id"] == "ValidatorAgent" and last_step.get("validation_result") in ("fail", "warning"):
            is_retry = True

    if mode == "design":
        if is_retry:
            return (
                f"[PMAgent] ValidatorAgent가 아래 사유로 이전 {output_name}를 반려하였다.\n"
                f"ValidationReport의 지적 사항을 반영하여 {output_name}를 처음부터 완전히 새로 작성하라.\n"
                f"이전 artifact를 복사하여 부분 수정하지 마라. 새 artifact를 독립적으로 생성하라.\n"
                f"특히 ID 참조(artifact_id, test_scenario_ids 등)가 현재 참조 대상의 실제 ID와 정확히 일치하는지 확인하라.\n\n"
                f"ValidationReport:\n{latest.get('ValidationReportArtifact', '')}\n\n"
                f"이전 {output_name} (참조용, 복사 금지):\n{latest.get(output_name, '')}\n\n"
                f"UseCaseModelArtifact:\n{latest.get('UseCaseModelArtifact', '')}"
            ) + _build_schema_reminder(agent_config, step)
        return (
            "아래 UseCaseModelArtifact를 기반으로 TestDesignArtifact를 작성하라.\n\n"
            f"UseCaseModelArtifact:\n{latest.get('UseCaseModelArtifact', '')}"
        ) + _build_schema_reminder(agent_config, step)

    # Execution mode (TestReportArtifact)
    parts = []
    if is_retry:
        parts.append(f"[PMAgent] ValidatorAgent가 아래 사유로 이전 {output_name}를 반려하였다.")
        parts.append(f"ValidationReport의 지적 사항을 반영하여 {output_name}를 처음부터 완전히 새로 작성하라.")
        parts.append("이전 artifact를 복사하여 부분 수정하지 마라. 새 artifact를 독립적으로 생성하라.")
        parts.append(
            "특히 ID 참조(artifact_id, source_artifact_ids, test_scenario_ids 등)가 현재 참조 대상의 실제 ID와 정확히 일치하는지 확인하라.\n"
        )
        parts.append(f"ValidationReport:\n{latest.get('ValidationReportArtifact', '')}\n")
        parts.append(f"이전 {output_name} (참조용, 복사 금지):\n{latest.get(output_name, '')}\n")
        parts.append("--- 참조 산출물 ---")
    else:
        parts.append(f"아래 artifacts를 기반으로 {output_name}를 작성하라.\n")

    parts.extend([
        f"TestDesignArtifact:\n{latest.get('TestDesignArtifact', '')}\n",
        f"ImplementationArtifact:\n{latest.get('ImplementationArtifact', '')}\n",
    ])

    # Inject source code context from narrative code blocks
    code_context = state.get("latest_code_blocks", {}).get("CodeAgent", "")
    if code_context:
        parts.append(f"--- 구현 소스코드 ---\n{code_context}\n")

    return "\n".join(parts) + _build_schema_reminder(agent_config, step)


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
        "- 절대로 사용자에게 질문하거나 확인/승인을 요청하지 마라. "
        "이 파이프라인은 완전 자동화되어 있으며, 사용자 입력을 받을 수 없다. "
        "프로젝트 이름, 폴더 구조, 기술 선택 등 모든 결정을 자율적으로 내려라.\n\n"
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

    termination_reason = state.get("termination_reason", "normal")
    if termination_reason != "normal":
        parts.append(
            "=== 종료/판정 컨텍스트 ===\n"
            f"- termination_reason: {termination_reason}\n"
            f"- termination_source_step: {state.get('termination_source_step')}\n"
            f"- termination_source_agent: {state.get('termination_source_agent', '')}\n"
            f"- latest_validation_result: {state.get('latest_validation_result', '')}\n"
        )

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

    # Inject source code context from narrative code blocks
    code_context = state.get("latest_code_blocks", {}).get("CodeAgent", "")
    if code_context:
        parts.append(f"--- 구현 소스코드 ---\n{code_context}\n")

    parts.append(
        "\n=== 판정 지침 ===\n"
        "위 '구현 소스코드' 섹션의 실제 코드를 직접 분석하라.\n"
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


def _strategy_pm_arbiter(
    agent_config: AgentConfig,
    step: StepDefinition,
    state: PipelineState,
) -> str:
    """PMAgent arbiter: decide routing after validator escalation.

    Receives the failure/warning context and all current artifacts.
    Must output ARBITER_ACTION with one of the 4 possible actions.
    """
    latest = state["latest_artifacts"]
    iteration = state["iteration_count"]
    termination_reason = state.get("termination_reason", "normal")
    source_step = state.get("termination_source_step", "?")
    rework_target = state.get("termination_rework_target", "")
    upstream_target = state.get("termination_upstream_target", "")
    rework_counts = state.get("rework_counts", {})
    max_reworks = state["max_reworks_per_gate"]

    parts = [
        f"Iteration {iteration}에서 ValidatorAgent가 검증 실패/경고를 발생시켰다.\n"
        f"너는 PMAgent 중재자(Arbiter)로서 다음 행동을 판정해야 한다.\n",
    ]

    parts.append(
        "=== 실패 컨텍스트 ===\n"
        f"- 종료 사유: {termination_reason}\n"
        f"- 발생 gate (step 번호): {source_step}\n"
        f"- 직전 작업 Agent (producer): {rework_target}\n"
        f"- 상위 Agent (upstream): {upstream_target}\n"
        f"- 현재 rework 횟수: {rework_counts}\n"
        f"- gate당 최대 rework: {max_reworks}\n"
    )

    parts.append(f"\n원본 User Story:\n{state['user_story']}\n")

    # 최근 ValidationReport 제공
    val_report = latest.get("ValidationReportArtifact", "")
    if val_report:
        parts.append(f"--- 최근 ValidationReportArtifact ---\n{val_report}\n")

    # 현재까지의 주요 artifacts 요약
    for atype in ["UseCaseModelArtifact", "ImplementationArtifact", "TestReportArtifact", "FeedbackArtifact"]:
        content = latest.get(atype, "")
        if content:
            # 긴 artifact는 처음 50줄만 전달
            lines = content.splitlines()
            if len(lines) > 50:
                content = "\n".join(lines[:50]) + "\n... (이하 생략)"
            parts.append(f"--- {atype} (요약) ---\n{content}\n")

    # 코드 context
    code_context = state.get("latest_code_blocks", {}).get("CodeAgent", "")
    if code_context:
        parts.append(f"--- 구현 소스코드 ---\n{code_context}\n")

    parts.append(
        "\n=== 판정 지침 ===\n"
        "위 컨텍스트를 분석하여 다음 중 하나의 행동을 선택하라:\n\n"
        "1. **accept_and_continue**: 경고를 수용하고 파이프라인의 다음 단계로 정상 진행한다.\n"
        "   - 적합한 경우: 경고(warning)가 치명적이지 않고, 현재 산출물로 다음 Agent가 작업 가능한 경우\n"
        "   - 검증 게이트를 통과시키는 것이며, Iteration을 종료하지 않는다.\n\n"
        "2. **retry_producer**: 직전 작업 Agent에게 1회 더 재작업을 지시한다.\n"
        f"   - 대상: {rework_target}\n"
        "   - 적합한 경우: 검증 실패가 단순 실수이고 같은 Agent가 수정 가능한 경우\n\n"
        "3. **retry_upstream**: 직전 Agent의 상위 Agent부터 재작업을 시작한다.\n"
        f"   - 대상: {upstream_target}\n"
        "   - 적합한 경우: 상위 단계의 산출물(요구사항, 테스트 설계 등)에 근본 원인이 있는 경우\n\n"
        "4. **restart_iteration**: 현재 Iteration을 ReqAgent부터 완전히 재시작한다.\n"
        "   - 적합한 경우: 요구사항 해석 자체가 잘못되었거나, 전체적인 방향 수정이 필요한 경우\n\n"
        "5. **end_iteration**: 현재 상태로 Iteration을 종료하고 최종 평가로 넘긴다.\n"
        "   - 적합한 경우: 추가 재작업이 무의미하고, 남은 파이프라인 단계도 실행할 필요가 없는 경우\n"
        "   - 주의: 이 선택은 남은 모든 단계(코드 구현, 테스트 실행 등)를 건너뛰고 즉시 Iteration 평가로 넘긴다.\n\n"
        "판정 기준:\n"
        "- 경고(warning)가 치명적이지 않으면 accept_and_continue가 가장 적절하다.\n"
        "- rework 횟수가 이미 최대에 도달했다면 retry_producer는 비효율적이다.\n"
        "- ValidationReport의 지적 사항이 단순 형식 오류인지, 근본적 설계 결함인지 구분하라.\n"
        "- restart_iteration은 비용이 크므로 신중히 선택하라.\n"
        "- end_iteration은 남은 단계를 모두 건너뛰므로, 정말로 진행이 불가능한 경우에만 선택하라.\n\n"
        "반드시 아래 형식의 판정 블록을 출력 마지막에 포함하라:\n"
        "```\n"
        "ARBITER_ACTION: retry_producer\n"
        "ARBITER_REASON: (판정 사유를 한 줄로 기술)\n"
        "```\n"
    )

    return "\n".join(parts)


_STRATEGIES: dict[str, callable] = {
    "req_agent": _strategy_req_agent,
    "validator": _strategy_validator,
    "input_assembler": _strategy_input_assembler,
    "test_agent": _strategy_test_agent,
    "pm_initializer": _strategy_pm_initializer,
    "pm_assessor": _strategy_pm_assessor,
    "pm_arbiter": _strategy_pm_arbiter,
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
