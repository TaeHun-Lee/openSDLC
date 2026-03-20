# Step 05 - Validator Criteria Draft

## 단계 대상 작업

- `TEST-DESIGN` 전용 Validator required checks 초안 정리
- `TEST-EXECUTION` 전용 Validator required checks 초안 정리
- `pass`, `warning`, `fail` 판정 기준과 blocking rule 초안 정리

## 작업 진행 계획

- 현재 `ValidationReportArtifact`의 `stage_check_guidance` 구조를 기준으로 확장 포인트를 도출한다.
- `TEST-DESIGN`에서 어떤 누락이 blocking인지 구분한다.
- `TEST-EXECUTION`에서 어떤 미실행/증거 부족이 blocking인지 구분한다.
- 이후 템플릿/프롬프트에 바로 반영 가능한 수준으로 단계별 체크리스트와 판정 규칙을 정리한다.

## 기대 효과

- 다음 단계 이후 실제 문서 반영 시 Validator 규칙이 모호하지 않게 된다.
- 테스트 설계 누락과 테스트 실행 부실을 서로 다른 기준으로 판정할 수 있다.
- 샘플 시뮬레이션에서 무엇이 통과/경고/실패인지 일관되게 비교할 수 있다.

## 예상 변경 범위

- 이번 단계는 Validator 기준 초안과 판정 규칙 설계에 집중한다.
- 실제 `ValidatorAgent.txt`, `ValidationReportArtifact.yaml` 파일은 아직 수정하지 않는다.
- 작업 이력 문서만 신규 생성한다.

## 작업 결과

### 1. `TEST-DESIGN` 전용 required checks 권장안

```yaml
TEST-DESIGN:
  required_checks:
    - "schema"
    - "traceability"
    - "acceptance_criteria_coverage"
    - "main_flow_coverage"
    - "precondition_coverage"
    - "trigger_coverage"
    - "observable_outcome_coverage"
    - "scenario_quality"
    - "evidence_type_definition"
    - "role_boundary"
```

각 체크의 의미:

- `schema`
  - `TestDesignArtifact` 필수 필드와 구조가 존재하는지
- `traceability`
  - 시나리오가 실제 `UC`의 use case와 연결되는지
- `acceptance_criteria_coverage`
  - 모든 AC가 적어도 하나 이상의 시나리오에 매핑되는지
- `main_flow_coverage`
  - `main_flow` 핵심 단계가 시나리오로 커버되는지
- `precondition_coverage`
  - 전제조건이 테스트 설계에서 빠지지 않았는지
- `trigger_coverage`
  - 사용자/시스템 트리거가 검증 기준에 포함됐는지
- `observable_outcome_coverage`
  - 결과 관찰 항목이 테스트 설계에 반영됐는지
- `scenario_quality`
  - 시나리오가 독립 실행 가능하고 과도하게 뭉쳐 있지 않은지
- `evidence_type_definition`
  - runtime/code/mixed 근거 요구가 시나리오별로 정의됐는지
- `role_boundary`
  - 테스트 설계가 구현 지시나 요구사항 재정의로 넘어가지 않았는지

### 2. `TEST-EXECUTION` 전용 required checks 권장안

```yaml
TEST-EXECUTION:
  required_checks:
    - "schema"
    - "test_design_traceability"
    - "scenario_execution_completeness"
    - "evidence_quality"
    - "evidence_type_consistency"
    - "defect_quality"
    - "score_consistency"
    - "role_boundary"
```

각 체크의 의미:

- `schema`
  - `TestReportArtifact` 구조와 필수 필드 존재 여부
- `test_design_traceability`
  - 각 실행 결과가 `TestDesignArtifact`의 시나리오를 참조하는지
- `scenario_execution_completeness`
  - 설계된 시나리오 중 누락된 실행이 없는지
- `evidence_quality`
  - evidence가 재검증 가능하고 구체적인지
- `evidence_type_consistency`
  - 설계된 evidence type과 실제 evidence 형태가 일치하는지
- `defect_quality`
  - defect가 실제 요구사항/행동 불일치 중심으로 기록됐는지
- `score_consistency`
  - pass/fail 개수, defect 심각도, satisfaction score가 서로 모순되지 않는지
- `role_boundary`
  - TestAgent가 구현 수정이나 피드백 작성 역할을 침범하지 않았는지

### 3. `TEST-DESIGN` 판정 기준 초안

#### `pass`

- 모든 AC가 시나리오에 매핑되어 있다
- `main_flow`, `preconditions`, `trigger`, `observable_outcome` 커버리지가 확보되어 있다
- 시나리오가 독립 실행 가능하다
- evidence type이 정의돼 있다
- downstream 구현과 실행 검증이 가능한 수준으로 충분히 명확하다

#### `warning`

- 전체 커버리지는 대체로 충족되지만 일부 시나리오 설명이 약하다
- 일부 evidence type 정의가 다소 모호하다
- 커버리지는 유지되지만 scenario granularity가 약간 거칠다
- downstream 진행은 가능하지만 테스트 누락 위험이 남아 있다

#### `fail`

- 하나 이상의 acceptance criteria가 어떤 시나리오에도 매핑되지 않는다
- `main_flow`의 핵심 단계가 누락된다
- 중요한 precondition 또는 trigger가 빠져 있다
- observable outcome이 검증 설계에서 빠져 downstream 검증이 불가능하다
- runtime evidence가 필요한데 code-only로 잘못 설계되어 있다
- 테스트 설계가 사실상 구현 추종형 설명 수준에 머무른다

### 4. `TEST-EXECUTION` 판정 기준 초안

#### `pass`

- 모든 필수 시나리오가 실행 또는 정당한 방식으로 검증되었다
- evidence가 구체적이고 재검증 가능하다
- defects와 score가 일관적이다
- `TestDesignArtifact`와 `TestReportArtifact` 간 traceability가 유지된다

#### `warning`

- 대부분의 시나리오는 실행되었지만 일부는 code-only 또는 간접 evidence로 검증되었다
- evidence 품질은 충분하나 실행 깊이가 다소 약하다
- score는 유효하지만 추가 runtime 검증이 있으면 더 좋다
- downstream 판단은 가능하지만 테스트 강도가 다소 부족하다

#### `fail`

- 설계된 필수 시나리오 중 하나 이상이 실행/검증되지 않았다
- evidence가 추상적이어서 재검증이 사실상 불가능하다
- 설계상 runtime evidence required인데 실제로는 code-only evidence만 제출되었다
- score와 defects가 서로 모순된다
- 주요 defect가 있는데 결과를 completion 수준으로 과대평가한다

### 5. blocking rule 초안

#### 즉시 blocking `fail`로 볼 항목

- AC 미매핑
- 핵심 `main_flow` 단계 누락
- 필수 precondition/trigger 누락
- `runtime evidence required` 시나리오에 대한 runtime 검증 누락
- 설계된 시나리오 미실행
- score와 defect 구조의 중대한 모순

#### `warning`으로 시작 가능한 항목

- 시나리오 설명 문장이 다소 거칠지만 커버리지는 충분한 경우
- evidence는 있으나 형식이 다소 약한 경우
- 실행 기반 검증이 더 바람직하지만 현재 단계에서 code/mixed evidence로도 합리적 설명이 가능한 경우
- 문구 수준의 중복이나 약간의 구조상 비효율

### 6. `ValidationReportArtifact` 반영 방향 메모

기존:

```yaml
TEST:
  required_checks:
    - "schema"
    - "evidence_quality"
    - "acceptance_criteria_mapping"
    - "score_consistency"
```

권장 개정:

```yaml
TEST-DESIGN:
  required_checks:
    - "schema"
    - "traceability"
    - "acceptance_criteria_coverage"
    - "main_flow_coverage"
    - "precondition_coverage"
    - "trigger_coverage"
    - "observable_outcome_coverage"
    - "scenario_quality"
    - "evidence_type_definition"
    - "role_boundary"

TEST-EXECUTION:
  required_checks:
    - "schema"
    - "test_design_traceability"
    - "scenario_execution_completeness"
    - "evidence_quality"
    - "evidence_type_consistency"
    - "defect_quality"
    - "score_consistency"
    - "role_boundary"
```

### 7. 단계별 next_action 기준 메모

- `TEST-DESIGN pass`
  - next agent: `CodeAgent`
- `TEST-DESIGN warning`
  - next agent: `PMAgent` decides `proceed` or `hold`
- `TEST-DESIGN fail`
  - next agent: `TestAgent [Design Mode]` rework

- `TEST-EXECUTION pass`
  - next agent: `CoordAgent`
- `TEST-EXECUTION warning`
  - next agent: `PMAgent` decides `proceed` or `hold`
- `TEST-EXECUTION fail`
  - next agent: 기본적으로 `TestAgent [Execution Mode]` rework
  - 단, 실패 원인이 구현 결함으로 명확하면 PMAgent가 `CodeAgent` 재작업 루프로 연결 가능

### 8. 현 단계 결론

- Validator는 `TEST-DESIGN`과 `TEST-EXECUTION`을 별도 품질 게이트로 다뤄야 한다.
- `TEST-DESIGN`은 커버리지 누락 여부를, `TEST-EXECUTION`은 설계-실행 정합성과 evidence 품질을 더 강하게 본다.
- 다음 단계부터는 이 기준을 실제 샘플 시뮬레이션에 적용해 실효성을 검증할 수 있다.

## 사용자 확인 상태

- 5단계 결과를 사용자에게 보고 후 확인 요청 예정
- 승인 시 6단계 `샘플 시뮬레이션 설계 또는 실제 문서 반영 준비`로 진행

## 다음 단계

- `Step 06 - Simulation Or Reflection Planning`
- 목표: `TetrisLikeGame` 등 사례에 적용할 샘플 시뮬레이션 범위와 산출물 계획 정리
