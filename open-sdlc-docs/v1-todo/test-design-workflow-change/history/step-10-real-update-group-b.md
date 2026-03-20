# Step 10 - Real Update Group B

## 단계 대상 작업

- 아티팩트 템플릿 실제 수정
- `TestDesignArtifact` 신규 추가
- `ImplementationArtifact`, `TestReportArtifact`, `ValidationReportArtifact`를 새 워크플로우에 맞게 정렬

## 작업 진행 계획

- `TestDesignArtifact.yaml`을 신규 추가한다.
- `ImplementationArtifact.yaml`에 `TestDesignArtifact` 참조와 테스트 시나리오 traceability를 반영한다.
- `TestReportArtifact.yaml`을 `TEST-EXECUTION` 전용 결과 아티팩트 구조로 확장한다.
- `ValidationReportArtifact.yaml`의 `stage_check_guidance`를 `TEST-DESIGN`, `TEST-EXECUTION` 기준으로 확장한다.

## 기대 효과

- 새 워크플로우를 실제 산출물 구조로 표현할 수 있게 된다.
- 이후 프롬프트가 따라야 할 템플릿 기준이 명확해진다.
- 테스트 설계와 테스트 실행이 물리적 아티팩트 수준에서 분리된다.

## 예상 변경 범위

- `open-sdlc-engine/templates/artifacts/TestDesignArtifact.yaml` 신규 추가
- `open-sdlc-engine/templates/artifacts/ImplementationArtifact.yaml`
- `open-sdlc-engine/templates/artifacts/TestReportArtifact.yaml`
- `open-sdlc-engine/templates/artifacts/ValidationReportArtifact.yaml`

## 작업 결과

### 수정 파일

- 신규 `open-sdlc-engine/templates/artifacts/TestDesignArtifact.yaml`
- `open-sdlc-engine/templates/artifacts/ImplementationArtifact.yaml`
- `open-sdlc-engine/templates/artifacts/TestReportArtifact.yaml`
- `open-sdlc-engine/templates/artifacts/ValidationReportArtifact.yaml`

### 반영 내용 요약

#### 1. `TestDesignArtifact.yaml` 신규 추가

- `artifact_id: "TD-{{id}}"` 구조 추가
- `coverage_plan`에 아래 커버리지 축을 포함
  - `acceptance_criteria`
  - `main_flow_steps`
  - `preconditions`
  - `triggers`
  - `observable_outcomes`
- `test_scenarios`에 scenario 단위 정의 및 `evidence_type`, `runtime_evidence_required`, `code_only_verification_allowed` 필드 추가
- `coverage_summary`에 `uncovered_items`, `design_notes` 추가

#### 2. `ImplementationArtifact.yaml` 수정

- `source_artifact_ids`에 `TD-{{source_test_design_id}}` 추가
- `implementation_target`에 `test_design_id` 추가
- `traceability`에 `test_scenario_ids` 추가
- 검증 지시 문구가 `UseCaseModelArtifact`, `TestDesignArtifact`, `ImplementationArtifact` 기준이 되도록 수정

#### 3. `TestReportArtifact.yaml` 수정

- `source_artifact_ids`에 `TD-{{source_test_design_id}}` 추가
- `test_scope`에 `test_design_id` 추가
- 각 `test_results`에 `related_test_scenario_id` 추가
- 검증 지시 문구에 `TestDesignArtifact` 추적성과 scenario 실행 여부 확인을 반영

#### 4. `ValidationReportArtifact.yaml` 수정

- 기존 `TEST` 단일 단계 required checks를 제거
- `TEST-DESIGN` required checks 추가
  - `acceptance_criteria_coverage`
  - `main_flow_coverage`
  - `precondition_coverage`
  - `trigger_coverage`
  - `observable_outcome_coverage`
  - `scenario_quality`
  - `evidence_type_definition`
- `TEST-EXECUTION` required checks 추가
  - `test_design_traceability`
  - `scenario_execution_completeness`
  - `evidence_quality`
  - `evidence_type_consistency`
  - `defect_quality`
  - `score_consistency`

### 수정 후 검토 결과

- `UC -> TD -> IMPL -> TEST` 참조 체인이 템플릿 수준에서 반영되었다.
- `ValidationReportArtifact`가 `TEST-DESIGN`과 `TEST-EXECUTION`을 별도 stage로 인식할 수 있게 되었다.
- `TestReportArtifact` 예시가 `TestDesignArtifact`의 시나리오 ID 구조와 맞도록 정렬되었다.

## 사용자 확인 상태

- 10단계 결과를 사용자에게 보고 후 확인 요청 예정
- 승인 시 다음 단계는 묶음 C 실제 수정으로 진행

## 다음 단계

- `Step 11 - Real Update Group C`
- 목표: `TestAgent`, `CodeAgent`, `ValidatorAgent`, `PMAgent` 프롬프트 실제 수정
