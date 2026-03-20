# OpenSDLC v1 Guide

## 1. 목적
`OpenSDLC_Guide.md`는 사람이 OpenSDLC v1의 실행 개념을 빠르게 파악하기 위한 참고용 운영 가이드다. 이 문서는 헌법과 엔진 문서의 상위 요약본이며, 실제 저장소 기준 최신 파이프라인과 역할 경계를 반영한다.

이 문서는 온보딩과 이해를 돕기 위한 요약 문서이며, 에이전트의 기본 실행 기준 문서는 아니다. 에이전트가 기본적으로 따라야 하는 기준은 `open-sdlc-constitution/`과 `open-sdlc-engine/` 문서 세트다.

## 2. OpenSDLC란 무엇인가
OpenSDLC는 SDLC의 각 단계를 AI 에이전트가 역할별로 수행하되, 모든 handoff를 구조화된 아티팩트로 고정하고, 각 단계를 독립 validator 게이트로 통제하는 `Artifact-Driven Execution` 기반 AI Software Factory 플랫폼이다.

핵심 특성은 다음과 같다.

- `Artifact-Driven Execution`
- `Spiral Iteration`
- `Strict Adherence`
- `Full Traceability`
- `Validation Over Self-Assertion`
- `No-Shortcut Principle`
- `Sequential Single-Agent Execution`
- `PMAgent Exclusive User Interaction`

## 3. 현재 공식 파이프라인

OpenSDLC v1의 현재 공식 파이프라인은 아래와 같다.

```text
User Story
-> UseCaseModelArtifact (UC)
-> ValidationReportArtifact (VAL)
-> TestDesignArtifact (TEST-DESIGN)
-> ValidationReportArtifact (VAL)
-> ImplementationArtifact (IMPL)
-> ValidationReportArtifact (VAL)
-> TestReportArtifact (TEST-EXECUTION)
-> ValidationReportArtifact (VAL)
-> FeedbackArtifact (FB)
-> ValidationReportArtifact (VAL)
-> verification_report.md
```

중요한 규칙:

- `TEST-DESIGN`은 구현 전에 반드시 존재해야 한다.
- `TEST-EXECUTION`은 구현 후에만 수행된다.
- 어느 단계도 생략, 병합, 압축할 수 없다.

## 4. 실행 제약

### Sequential Single-Agent Execution
- 특정 시점에는 오직 하나의 OpenSDLC 에이전트만 활성화된다.
- 여러 에이전트를 동시에 실행하거나 동시에 실행되는 것처럼 보고하면 안 된다.
- OpenSDLC가 활성화된 동안에는 병렬 툴 호출도 순차 실행 규칙을 침해할 수 있으므로 금지된다.

### PMAgent Exclusive User Interaction
- 사용자 입력 요청과 승인 요청은 `PMAgent`만 수행한다.
- 다른 에이전트는 자신의 진행을 1인칭으로 보고할 수는 있지만, 사용자에게 입력을 요구하지 않는다.

### Validation Over Self-Assertion
- 모든 전문 에이전트 산출물은 `ValidatorAgent`가 독립 검증한다.
- `pass`, `warning`, `fail` 중 하나로 판정되며, `fail`은 다음 단계 진행을 차단한다.

## 5. 에이전트 구성

| 에이전트 | 역할 | 산출물 |
| :--- | :--- | :--- |
| `PMAgent` | 사용자 인터페이스, workspace 준비, handoff 통제, iteration 종합 보고 | `verification_report.md` |
| `ReqAgent` | 요구사항 구조화 및 use case 모델 정의 | `UseCaseModelArtifact` |
| `ValidatorAgent` | 각 단계 산출물의 독립 감사와 workflow gate 판정 | `ValidationReportArtifact` |
| `TestAgent` | 구현 전 테스트 설계, 구현 후 테스트 실행 | `TestDesignArtifact`, `TestReportArtifact` |
| `CodeAgent` | 승인된 요구와 테스트 설계를 기준으로 구현 | `ImplementationArtifact` |
| `CoordAgent` | 테스트 결과를 다음 iteration 요구 또는 완료 권고로 변환 | `FeedbackArtifact` |

## 6. 주요 아티팩트

### UseCaseModelArtifact
- 원문 사용자 요청을 그대로 보존한다.
- `decomposition_basis`를 통해 왜 use case를 그렇게 나눴는지 설명한다.
- 각 use case는 독립 end-to-end 테스트 단위여야 한다.

### TestDesignArtifact
- 구현 전에 테스트 범위, 커버리지, 시나리오, evidence 유형을 고정한다.
- `acceptance_criteria`, `main_flow`, `preconditions`, `trigger`, `observable_outcome`를 모두 덮어야 한다.

### ImplementationArtifact
- 구현 대상, 변경 파일, 런타임 정보, 추적 근거를 기록한다.
- `source_artifact_ids`에는 최소 `UC`와 `TEST-DESIGN`이 포함되어야 한다.

### TestReportArtifact
- 설계된 시나리오의 실행 결과를 남긴다.
- `defects`, `improvements`, `requirement_coverage`, `satisfaction_score`를 포함한다.

### FeedbackArtifact
- 점수와 결함 상태를 바탕으로 다음 iteration 필요 여부 또는 완료 권고 여부를 기록한다.
- `CoordAgent -> PMAgent -> ReqAgent` 전달 경로를 유지해야 한다.

### ValidationReportArtifact
- 단계별 공통 체크와 stage-specific check 결과를 기록한다.
- `validated_stage`는 `UC`, `TEST-DESIGN`, `IMPL`, `TEST-EXECUTION`, `FB` 중 하나여야 한다.

## 7. 상태값과 판정

### 아티팩트 상태값
- `draft`
- `approved`
- `implemented`
- `feedback-required`
- `actionable`
- `completed`

### Validation 판정값
- `pass`
- `warning`
- `fail`

정렬 규칙:
- `pass -> approved`
- `warning -> actionable`
- `fail -> feedback-required`

## 8. 보고 원칙

OpenSDLC는 실제 작업 주체가 자신의 관점에서 직접 보고한다.

기본 원칙:
- 현재 활성 에이전트가 자기 이름으로 1인칭 보고를 수행한다.
- 보고에는 시작 내용, 생성 산출물, 다음 에이전트가 포함되어야 한다.
- `PMAgent`는 다른 에이전트의 작업을 대리 서술하지 않고, handoff와 승인 요청을 통제한다.

## 9. 품질 게이트

모든 단계는 공통적으로 아래 항목을 검사한다.

- `schema`
- `traceability`
- `evidence`
- `decision_consistency`
- `role_boundary`
- `no_regression`

추가로 단계별 전용 체크가 존재한다.

- `UC`: `scope_clarity`, `acceptance_criteria_testability`, `instruction_completeness`, `e2e_decomposition_quality`, `failure_mode_separation`
- `TEST-DESIGN`: `acceptance_criteria_coverage`, `main_flow_coverage`, `precondition_coverage`, `trigger_coverage`, `observable_outcome_coverage`, `scenario_quality`, `evidence_type_definition`
- `IMPL`: `scope_adherence`, `implementation_consistency`
- `TEST-EXECUTION`: `test_design_traceability`, `scenario_execution_completeness`, `evidence_quality`, `evidence_type_consistency`, `defect_quality`, `score_consistency`
- `FB`: `defect_task_mapping`, `done_criteria_testability`, `decision_consistency`, `reqagent_handoff_boundary`

## 10. 이터레이션 규칙

- `satisfaction_score < 90`
  - 다음 iteration을 권고한다.
  - 사용자 승인 후 다음 requirement cycle을 시작한다.
- `satisfaction_score >= 90`
  - 최신 validation 결과에 blocking `fail`이 없으면 완료 권고가 가능하다.
- 최종 프로젝트 종료
  - 반드시 사용자의 명시적 승인이 필요하다.

## 11. 실행 결과 예시

OpenSDLC v1을 실제로 실행하면 보통 `workspace/{ProjectName}/` 아래에 iteration 결과가 누적된다.

예시 구조:

```text
workspace/{ProjectName}/
  dev/
  iteration-01/
    artifacts/
    verification_report.md
  iteration-02/
    artifacts/
    verification_report.md
```

- `dev/`는 최신 구현 상태를 유지한다.
- 각 iteration은 자신의 아티팩트 세트와 `verification_report.md`를 별도로 가진다.
- `workspace/`는 런타임 결과물이며 `.gitignore` 대상일 수 있으므로, 저장소를 새로 클론했을 때 항상 실제 예시 프로젝트가 들어 있지는 않을 수 있다.

## 12. 관련 문서

- [README.md](../README.md)
- [core-concept.md](../open-sdlc-engine/core-concepts/core-concept.md)
- [workflow.md](../open-sdlc-engine/core-concepts/workflow.md)
- [agent-definitions.md](../open-sdlc-engine/core-concepts/agent-definitions.md)
- [llm-execution-lock.md](../open-sdlc-engine/core-concepts/llm-execution-lock.md)
