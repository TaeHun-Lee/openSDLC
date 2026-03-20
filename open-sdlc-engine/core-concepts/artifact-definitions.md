# Artifact 정의

**Artifact**는 단순한 문서가 아니라, 구조화된 테이터이면서 다음 에이전트의 작업 지시서입니다.

## 1. Artifact의 핵심 구성 요소
에이전트가 생성하는 모든 아티팩트는 다음 정보를 포함해야 합니다.
- **Context**: 이 아티팩트의 목적과 배경
- **Instruction**: 다음 에이전트가 수행해야 할 구체적인 작업
- **Verification**: 작업 결과를 어떻게 검증할지에 대한 기준

## 2. Artifact 종류 및 흐름

실제 한 이터레이션의 표준 흐름은 다음과 같습니다.

`UC -> VAL -> TEST-DESIGN -> VAL -> IMPL -> VAL -> TEST-EXECUTION -> VAL -> FB -> VAL`

즉 `ValidationReportArtifact`는 단일 보조 산출물이 아니라, 각 전문 에이전트 산출물 뒤에 반복적으로 생성되는 단계별 품질 게이트입니다.

### 1) UseCaseModelArtifact (UC)
- **생성**: ReqAgent
- **목적**: 사용자 원문 요청(`raw_user_request`)을 보존한 상태로 User Story를 실행 가능한 Use Case 단위로 정제하고 구현/테스트의 기준을 정의합니다.
- **스키마**: `open-sdlc-engine/templates/artifacts/UseCaseModelArtifact.yaml`

### 2) TestDesignArtifact (TEST-DESIGN)
- **생성**: TestAgent
- **목적**: 구현 전에 use case별 테스트 시나리오, 커버리지, evidence 기준을 고정합니다.
- **스키마**: `open-sdlc-engine/templates/artifacts/TestDesignArtifact.yaml`

### 3) ImplementationArtifact (IMPL)
- **생성**: CodeAgent
- **목적**: 어떤 기능이 구현되었고 어떤 파일이 변경되었는지 보고하며, 구현의 한계를 명시합니다.
- **스키마**: `open-sdlc-engine/templates/artifacts/ImplementationArtifact.yaml`

### 4) ValidationReportArtifact (VAL)
- **생성**: ValidatorAgent
- **목적**: 직전 단계 아티팩트가 규칙을 준수하는지 독립적으로 감사하고, 다음 단계 진행 또는 재작업 여부를 판정합니다.
- **특징**: UC, TEST-DESIGN, IMPL, TEST-EXECUTION, FB 뒤에 각각 반복 생성될 수 있으며 `validated_stage`로 검증 단계를 구분합니다.
- **상태 의미**:
  - `approved`: 검증 통과, 다음 단계 진행 가능
  - `actionable`: 비차단 경고 존재, PMAgent가 진행/보류를 결정
  - `feedback-required`: 검증 실패, 원 생성 에이전트 재작업 필요
- **스키마**: `open-sdlc-engine/templates/artifacts/ValidationReportArtifact.yaml`

### 5) TestReportArtifact (TEST-EXECUTION)
- **생성**: TestAgent
- **목적**: 승인된 `TestDesignArtifact`를 기준으로 테스트 실행 결과와 만족도 점수, 결함 사항을 기록합니다.
- **스키마**: `open-sdlc-engine/templates/artifacts/TestReportArtifact.yaml`

### 6) FeedbackArtifact (FB)
- **생성**: CoordAgent
- **목적**: 테스트 결과를 다음 이터레이션의 개발 지침(Prompt)으로 변환하여 전달합니다.
- **핵심 필드**: `feedback_reason`, `priority_tasks`, `feedback_delivery`, `prompt_for_next_iteration`, `done_criteria`
- **스키마**: `open-sdlc-engine/templates/artifacts/FeedbackArtifact.yaml`

---

## 3. 작명 및 관리 규칙
- **ID 패턴**:
  - UseCaseModelArtifact: `UC-<number>`
  - TestDesignArtifact: `TD-<number>`
  - ImplementationArtifact: `IMPL-<number>`
  - ValidationReportArtifact: `<target_artifact_id>-VAL-<attempt>`
  - TestReportArtifact: `TEST-<number>`
  - FeedbackArtifact: `FB-<number>`
- **Validation ID 예시**:
  - `UC-01-VAL-01`
  - `TD-01-VAL-01`
  - `IMPL-01-VAL-01`
  - `IMPL-01-VAL-02`
  - `TEST-01-VAL-01`
- **추적성**: 모든 아티팩트는 `source_artifact_ids` 필드를 통해 상위 아티팩트를 참조해야 합니다. (예: IMPL은 반드시 UC와 TD를 참조)
