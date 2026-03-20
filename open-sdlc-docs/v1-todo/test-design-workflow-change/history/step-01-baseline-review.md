# Step 01 - Current v1 Baseline Review

## 단계 대상 작업

- 현재 OpenSDLC v1의 공식 워크플로우 기준선 확인
- 테스트 단계 관련 문서, 프롬프트, 템플릿의 실제 정의 확인
- 변경 대상 문서와 신규 필요 가능 항목 분류

## 작업 진행 계획

- `workflow.md`, `core-concept.md`, `agent-definitions.md`를 읽고 현재 파이프라인 정의를 확인한다.
- `TestAgent.txt`, `ValidatorAgent.txt`를 읽고 테스트 단계 책임과 검증 기준을 확인한다.
- `TestReportArtifact.yaml`, `ValidationReportArtifact.yaml`를 읽고 현재 스키마 구조를 확인한다.
- 문서별로 `유지`, `수정`, `신규 필요 가능` 항목을 정리한다.

## 기대 효과

- 실제 문서 기준으로 현재 구조를 명확히 파악할 수 있다.
- 이후 단계에서 변경 범위를 통제할 수 있다.
- 워크플로우 개정 초안 작성 전에 기준선이 고정된다.

## 예상 변경 범위

- 본 단계는 기준선 확인 단계이므로 파일 수정 없이 읽기/분석 중심으로 진행한다.
- 필요 시 다음 단계부터 구조 제안 또는 문서 수정으로 확장한다.

## 작업 결과

### 현재 공식 기준선

- 공식 파이프라인은 `UC -> VAL -> IMPL -> VAL -> TEST -> VAL -> FB -> VAL`이다.
- 이 정의는 아래 문서들에 일관되게 반영되어 있다.
  - `open-sdlc-engine/core-concepts/workflow.md`
  - `open-sdlc-engine/core-concepts/core-concept.md`
  - `open-sdlc-engine/core-concepts/agent-definitions.md`

### 테스트 단계 관련 기준선

- 현재 `TestAgent`는 테스트 설계와 테스트 실행/평가를 한 단계에서 모두 담당한다.
- `TestReportArtifact`는 구현 이후 산출되는 단일 테스트 결과 보고서 구조다.
- `ValidatorAgent`의 TEST 단계 검증 기준은 현재 아래 항목 중심이다.
  - `evidence_quality`
  - `acceptance_criteria_mapping`
  - `score_consistency`

### 구조적 확인 사항

- `main_flow`, `preconditions`, `trigger`, `observable_outcome`에 대한 별도 커버리지 강제 구조는 현재 공식 문서에 없다.
- 따라서 TEST-DESIGN 단계를 도입하려면 워크플로우 문서뿐 아니라 프롬프트/템플릿/Validator 기준까지 함께 조정해야 한다.

### 변경 대상 분류

#### 수정 필요

- `open-sdlc-engine/core-concepts/workflow.md`
- `open-sdlc-engine/core-concepts/core-concept.md`
- `open-sdlc-engine/core-concepts/agent-definitions.md`
- `open-sdlc-engine/prompts/agent/TestAgent.txt`
- `open-sdlc-engine/prompts/agent/ValidatorAgent.txt`
- `open-sdlc-engine/templates/artifacts/TestReportArtifact.yaml`
- `open-sdlc-engine/templates/artifacts/ValidationReportArtifact.yaml`

#### 신규 가능성 높음

- `open-sdlc-engine/templates/artifacts/TestDesignArtifact.yaml`
- `open-sdlc-engine/prompts/agent/TestDesignAgent.txt`
  - 또는 기존 `TestAgent`를 Design/Execution 모드로 확장

#### 유지 가능

- `ReqAgent`, `CodeAgent`, `CoordAgent` 관련 문서는 현재 기준으로 직접 영향이 상대적으로 작다.
- 다만 이후 단계에서 참조 체인 조정이 필요하면 일부 수정 가능성이 있다.

## 사용자 확인 상태

- 1단계 결과를 사용자에게 보고 완료
- 다음 단계 진행 전 사용자 확인 요청 상태

## 다음 단계

- `Step 02 - Workflow Draft`
- 목표: `TEST-DESIGN`과 `TEST-EXECUTION`을 포함한 개정 워크플로우 초안 정리
