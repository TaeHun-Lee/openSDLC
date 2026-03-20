# Step 03 - Artifact Structure Draft

## 단계 대상 작업

- `TestDesignArtifact` 신규 구조 초안 정리
- `TestReportArtifact`의 역할을 실행/검증 중심으로 재정의
- `ValidationReportArtifact`의 단계 구분 및 required checks 확장 방향 정리

## 작업 진행 계획

- 현재 `TestReportArtifact`와 `ValidationReportArtifact` 구조를 기준으로 부족한 점을 식별한다.
- `TEST-DESIGN` 단계에서 반드시 표현되어야 하는 테스트 설계 정보를 신규 아티팩트 구조로 정리한다.
- `TEST-EXECUTION` 단계에서는 어떤 정보만 남기고 어떤 정보는 `TEST-DESIGN`으로 이동해야 하는지 재배치한다.
- Validator가 새 구조를 검사할 수 있도록 단계 구분과 체크 항목 확장 방향을 정리한다.

## 기대 효과

- 다음 단계에서 프롬프트와 validator 규칙을 바꿀 때 기준이 명확해진다.
- 테스트 설계와 테스트 실행의 책임이 아티팩트 수준에서 분리된다.
- 샘플 시뮬레이션 전에 필요한 최소 스키마가 고정된다.

## 예상 변경 범위

- 이번 단계는 템플릿 설계 초안과 필드 설계 메모 정리에 집중한다.
- 실제 `yaml` 템플릿 파일은 아직 수정하지 않는다.
- 작업 이력 문서만 신규 생성한다.

## 작업 결과

### 1. 신규 아티팩트 도입 권장안

- 신규 아티팩트 `TestDesignArtifact` 도입이 필요하다.
- 이유:
  - `무엇을 테스트할지`를 구현 전에 고정할 별도 구조가 필요하다.
  - 기존 `TestReportArtifact`에 설계 정보와 실행 결과를 함께 넣으면 다시 역할 혼합이 발생한다.
  - CodeAgent가 참조해야 하는 테스트 기준은 실행 결과가 아니라 설계된 시나리오여야 한다.

### 2. `TestDesignArtifact` 초안 구조

권장 ID 및 메타데이터:

```yaml
artifact_id: "TD-{{id}}"
artifact_type: "TestDesignArtifact"
iteration: {{iteration}}
created_by: "TestAgent"
created_at: "{{timestamp}}"
source_artifact_ids:
  - "UC-{{source_usecase_id}}"
status: "draft"
summary: "{{this_artifact_summary}}"
instructions_for_next_agent: |
  TestDesignArtifact를 검증하라.
  coverage completeness와 scenario quality를 확인하라.
```

권장 본문 구조:

```yaml
test_design_scope:
  use_case_ids:
    - "UC-{{source_usecase_id}}-01"

coverage_plan:
  acceptance_criteria:
    - item: "{{ac_1}}"
      covered_by_scenarios:
        - "TS-{{id}}-01"
  main_flow_steps:
    - item: "{{main_flow_step_1}}"
      covered_by_scenarios:
        - "TS-{{id}}-01"
  preconditions:
    - item: "{{precondition_1}}"
      covered_by_scenarios:
        - "TS-{{id}}-01"
  triggers:
    - item: "{{trigger_1}}"
      covered_by_scenarios:
        - "TS-{{id}}-01"
  observable_outcomes:
    - item: "{{observable_outcome_1}}"
      covered_by_scenarios:
        - "TS-{{id}}-01"

test_scenarios:
  - scenario_id: "TS-{{id}}-01"
    related_use_case_id: "UC-{{source_usecase_id}}-01"
    purpose: "{{scenario_purpose}}"
    setup: "{{setup}}"
    action: "{{action}}"
    expected_result: "{{expected_result}}"
    evidence_type: "{{runtime_or_code_or_mixed}}"
    runtime_evidence_required: true
    code_only_verification_allowed: false

coverage_summary:
  uncovered_items: []
  design_notes:
    - "{{design_note_1}}"
```

### 3. `TestDesignArtifact` 필드 목적

- `coverage_plan`
  - 테스트 시나리오가 무엇을 커버하는지 명시적으로 연결하기 위해 필요
  - 단순 AC 매핑만이 아니라 `main_flow`, `preconditions`, `trigger`, `observable_outcomes`까지 커버해야 함

- `test_scenarios`
  - 실제 실행 가능한 테스트 설계 단위
  - CodeAgent와 TestAgent Execution Mode 모두가 참조할 기준점

- `evidence_type`
  - 해당 시나리오가 `runtime`, `code`, `mixed` 중 어떤 근거를 요구하는지 사전에 고정

- `runtime_evidence_required`
  - 코드만 읽어서는 충분하지 않은 시나리오를 명확히 구분하기 위해 필요

- `code_only_verification_allowed`
  - 정적 구조 확인만으로 충분한 테스트인지 구분하기 위해 필요

- `coverage_summary.uncovered_items`
  - 커버하지 못한 항목을 의도적으로 비워두지 않고 드러내기 위해 필요

### 4. `TestReportArtifact` 재정의 방향

현재 `TestReportArtifact`는 테스트 설계와 실행 결과의 흔적이 혼합될 수 있다.

개정 후 역할:
- `TestReportArtifact`는 **오직 TEST-EXECUTION 결과 보고서**로 사용한다.
- 즉 "무엇을 테스트할지"는 담지 않고 "설계된 테스트를 실제 수행한 결과"만 담는다.

권장 변경 포인트:

- `source_artifact_ids`에 `TD-{{source_test_design_id}}` 추가 필요
- `test_scope`는 유지 가능하되, `test_design_reference`를 명시하는 편이 좋음
- `test_results`는 `scenario_id` 또는 `related_test_scenario_id`를 포함해야 함
- evidence는 `TestDesignArtifact`의 기대 evidence type과 맞는지 검증 가능해야 함

권장 개편 예시:

```yaml
source_artifact_ids:
  - "UC-{{source_usecase_id}}"
  - "TD-{{source_test_design_id}}"
  - "IMPL-{{source_impl_id}}"

test_results:
  - test_case_id: "TC-{{id}}-01"
    related_use_case_id: "UC-{{source_usecase_id}}-01"
    related_test_scenario_id: "TS-{{source_test_design_id}}-01"
    validation_basis: "{{code_or_execution_or_mixed}}"
    result: "pass"
    evidence: "{{evidence_1}}"
```

### 5. `TestReportArtifact`에서 이동 또는 축소되어야 할 책임

- 테스트 설계 논리
- 커버리지 설계 자체
- 무엇을 테스트해야 하는지의 신규 정의

위 항목은 앞으로 `TestDesignArtifact`가 맡는 것이 적절하다.

### 6. `ValidationReportArtifact` 확장 방향

현재는 `validated_stage`가 `UC`, `IMPL`, `TEST`, `FB` 정도로만 해석된다.
개정 후에는 최소 아래 단계 구분이 필요하다.

```yaml
validated_stage: "TEST-DESIGN"
```

또는

```yaml
validated_stage: "TEST-EXECUTION"
```

`stage_check_guidance` 확장 권장안:

```yaml
TEST-DESIGN:
  required_checks:
    - "schema"
    - "acceptance_criteria_coverage"
    - "main_flow_coverage"
    - "precondition_coverage"
    - "trigger_coverage"
    - "observable_outcome_coverage"
    - "scenario_quality"

TEST-EXECUTION:
  required_checks:
    - "schema"
    - "test_design_traceability"
    - "scenario_execution_completeness"
    - "evidence_quality"
    - "score_consistency"
```

### 7. Validator 관점에서 필요한 구조 변화

- `TEST-DESIGN` 검증 시:
  - AC만 커버했는지
  - `main_flow`와 `preconditions`가 빠지지 않았는지
  - runtime evidence가 필요한 시나리오가 명확히 지정됐는지

- `TEST-EXECUTION` 검증 시:
  - 실제 결과가 설계된 시나리오를 참조하는지
  - 설계된 시나리오 중 누락된 실행이 있는지
  - evidence type이 설계와 일치하는지

### 8. 현 단계 결론

- `TestDesignArtifact`는 신규 도입하는 것이 적절하다.
- `TestReportArtifact`는 유지하되 `TEST-EXECUTION` 전용 결과 보고서로 축소/명확화하는 것이 적절하다.
- `ValidationReportArtifact`는 `TEST` 단일 단계 검증 구조에서 `TEST-DESIGN`과 `TEST-EXECUTION`을 구분하는 구조로 확장해야 한다.

## 사용자 확인 상태

- 3단계 결과를 사용자에게 보고 후 확인 요청 예정
- 승인 시 4단계 `에이전트 책임과 프롬프트 개정 초안`으로 진행

## 다음 단계

- `Step 04 - Agent And Prompt Draft`
- 목표: `TestAgent` 2모드 구조를 기준으로 관련 프롬프트 및 책임 정의 변경 방향 정리
