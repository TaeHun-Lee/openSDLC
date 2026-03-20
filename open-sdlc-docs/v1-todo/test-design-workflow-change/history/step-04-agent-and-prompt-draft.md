# Step 04 - Agent And Prompt Draft

## 단계 대상 작업

- `TestAgent` 2모드 구조 기준으로 에이전트 책임 재정의
- 관련 프롬프트 개정 방향 정리
- `CodeAgent`, `ValidatorAgent`, `PMAgent`에 필요한 연쇄 변경 포인트 정리

## 작업 진행 계획

- 현재 `agent-definitions.md`와 관련 프롬프트의 책임 구조를 기준으로 변경 지점을 식별한다.
- `TestAgent`를 `Design Mode`와 `Execution Mode`로 구분한 책임 초안을 정리한다.
- 새 워크플로우에서 `CodeAgent`, `ValidatorAgent`, `PMAgent`가 읽어야 할 입력과 handoff 규칙을 정리한다.
- 실제 프롬프트 파일 수정 전에 역할별 개정 포인트를 문장 수준으로 고정한다.

## 기대 효과

- 다음 단계에서 Validator 기준과 이후 문서 반영 시 충돌을 줄일 수 있다.
- 어떤 에이전트가 무엇을 읽고 무엇을 출력하는지 명확해진다.
- `TestDesignArtifact` 도입에 따른 연쇄 영향이 정리된다.

## 예상 변경 범위

- 이번 단계는 책임/프롬프트 개정 초안 정리에 집중한다.
- 실제 프롬프트 파일 본문은 아직 수정하지 않는다.
- 작업 이력 문서만 신규 생성한다.

## 작업 결과

### 1. `TestAgent` 책임 재정의 권장안

v1 실험 단계에서는 `TestAgent`를 신규 에이전트로 분리하지 않고, 아래 두 모드로 운영하는 방식을 유지한다.

#### `TestAgent [Design Mode]`

- 입력:
  - 승인된 `UseCaseModelArtifact`
  - 최신 `ValidationReportArtifact` for `UC`
- 출력:
  - `TestDesignArtifact`
- 역할:
  - 구현 전에 테스트 시나리오를 설계한다.
  - `acceptance_criteria`뿐 아니라 `main_flow`, `alternate_flows`, `preconditions`, `trigger`, `observable_outcome`까지 읽고 커버리지를 설계한다.
  - 각 시나리오별 요구 evidence type과 runtime verification 필요 여부를 고정한다.

#### `TestAgent [Execution Mode]`

- 입력:
  - 승인된 `UseCaseModelArtifact`
  - 승인된 `TestDesignArtifact`
  - 승인된 `ImplementationArtifact`
  - 최신 `ValidationReportArtifact` for `IMPL`
- 출력:
  - `TestReportArtifact`
- 역할:
  - 새 테스트를 설계하는 것이 아니라, 이미 설계된 시나리오를 실행/검증한다.
  - 시나리오별 결과, evidence, defects, improvements, satisfaction score를 기록한다.
  - `TestDesignArtifact`와 구현 결과 사이의 불일치를 명시적으로 드러낸다.

### 2. `TestAgent.txt` 개정 방향

현재 `TestAgent.txt`는 설계와 실행이 혼합돼 있다.

개정 방향:

- 문서 상단에서 모드를 명시적으로 구분한다.
  - `Design Mode`
  - `Execution Mode`

- `Design Mode` 필수 읽기 대상:
  - `UseCaseModelArtifact`
  - 최신 `UC ValidationReportArtifact`

- `Design Mode` 필수 작업:
  - use case별 테스트 시나리오 설계
  - AC, main flow, preconditions, triggers, observable outcomes 커버리지 기록
  - evidence type 정의
  - runtime evidence required 여부 정의

- `Execution Mode` 필수 읽기 대상:
  - `UseCaseModelArtifact`
  - `TestDesignArtifact`
  - `ImplementationArtifact`
  - 최신 `IMPL ValidationReportArtifact`

- `Execution Mode` 필수 작업:
  - 설계된 시나리오 기준으로 실행/검증
  - 누락된 시나리오 또는 미실행 항목 식별
  - 결과/evidence/defects/score 기록

### 3. `CodeAgent` 연쇄 변경 필요 사항

현재 `CodeAgent`는 `UC`와 `UC Validation`만을 핵심 입력으로 본다.

개정 후 필요 사항:

- 입력에 `TestDesignArtifact`와 최신 `TEST-DESIGN ValidationReportArtifact` 추가 필요
- 구현 시 고려 항목에 아래가 포함되어야 한다.
  - 어떤 시나리오가 runtime evidence를 요구하는가
  - 어떤 전제조건이 반드시 충족되어야 하는가
  - 어떤 observable outcome이 코드 구조만으로는 충분하지 않은가

권장 문장 변경 방향:

- 기존:
  - "the UseCaseModelArtifact"
- 개정:
  - "the approved UseCaseModelArtifact and approved TestDesignArtifact"

### 4. `ValidatorAgent` 연쇄 변경 필요 사항

현재 `ValidatorAgent`는 `TEST` 단일 단계만 상정하고 있다.

개정 후 필요 사항:

- `TestDesignArtifact`를 독립 검증 대상으로 추가
- `validated_stage`가 최소 아래를 구분할 수 있어야 함
  - `TEST-DESIGN`
  - `TEST-EXECUTION`

- `TEST-DESIGN`에서 확인할 것:
  - AC coverage completeness
  - main flow coverage
  - precondition coverage
  - trigger coverage
  - observable outcome coverage
  - scenario quality

- `TEST-EXECUTION`에서 확인할 것:
  - test design traceability
  - scenario execution completeness
  - evidence quality
  - score consistency

### 5. `PMAgent` 연쇄 변경 필요 사항

현재 `PMAgent`는 `UC`, `IMPL`, `TEST`, `FB` 단계만 관리한다.

개정 후 필요 사항:

- handoff 순서에 `TEST-DESIGN -> VAL` 단계를 추가해야 한다.
- iteration artifact completeness 점검 시 아래를 확인해야 한다.
  - `UC`
  - `UC-VAL`
  - `TEST-DESIGN`
  - `TEST-DESIGN-VAL`
  - `IMPL`
  - `IMPL-VAL`
  - `TEST-EXECUTION`
  - `TEST-EXECUTION-VAL`
  - `FB`
  - `FB-VAL`

- `verification_report.md` 작성 시 TEST 관련 검증 요약도 둘로 나눠야 한다.
  - Test Design Validation
  - Test Execution Validation

### 6. `agent-definitions.md` 개정 방향

문서 변경을 최소화하는 방향에서는 에이전트 종류를 그대로 유지하되, `TestAgent` 설명을 두 모드로 확장하는 것이 적절하다.

권장 변경 포인트:

- `TestAgent`
  - "품질 검증 및 결과 보고"에서
  - "테스트 설계와 실행 검증을 단계적으로 수행"으로 확장

- `CodeAgent`
  - 입력 기준에 `TestDesignArtifact` 참조 추가

- `ValidatorAgent`
  - `TestDesignArtifact` 검증 대상 추가

- `PMAgent`
  - 새 handoff 단계와 artifact completeness 점검 규칙 추가

### 7. 단계별 입력/출력 책임 매트릭스 초안

| Agent | Mode | Inputs | Output |
| :--- | :--- | :--- | :--- |
| `ReqAgent` | N/A | User Story | `UseCaseModelArtifact` |
| `ValidatorAgent` | UC | `UseCaseModelArtifact` | `ValidationReportArtifact` |
| `TestAgent` | Design | `UseCaseModelArtifact`, `UC Validation` | `TestDesignArtifact` |
| `ValidatorAgent` | TEST-DESIGN | `TestDesignArtifact` | `ValidationReportArtifact` |
| `CodeAgent` | N/A | `UseCaseModelArtifact`, `TestDesignArtifact`, latest validations | `ImplementationArtifact` |
| `ValidatorAgent` | IMPL | `ImplementationArtifact` | `ValidationReportArtifact` |
| `TestAgent` | Execution | `UseCaseModelArtifact`, `TestDesignArtifact`, `ImplementationArtifact`, `IMPL Validation` | `TestReportArtifact` |
| `ValidatorAgent` | TEST-EXECUTION | `TestReportArtifact` | `ValidationReportArtifact` |
| `CoordAgent` | N/A | `TestReportArtifact` | `FeedbackArtifact` |
| `ValidatorAgent` | FB | `FeedbackArtifact` | `ValidationReportArtifact` |
| `PMAgent` | N/A | Full iteration artifacts | `verification_report.md` |

### 8. 현 단계 결론

- `TestAgent`는 v1 실험 단계에서 2모드 구조로 재정의하는 것이 적절하다.
- `CodeAgent`, `ValidatorAgent`, `PMAgent`는 모두 `TestDesignArtifact` 도입의 영향을 받으므로 함께 개정해야 한다.
- 다음 단계에서는 이 구조를 기준으로 Validator 판정 기준을 더 구체적으로 정의하는 것이 적절하다.

## 사용자 확인 상태

- 4단계 결과를 사용자에게 보고 후 확인 요청 예정
- 승인 시 5단계 `Validator 판정 기준 개정 초안`으로 진행

## 다음 단계

- `Step 05 - Validator Criteria Draft`
- 목표: `TEST-DESIGN` 및 `TEST-EXECUTION` 전용 판정 기준과 `pass/warning/fail` 규칙 정리
