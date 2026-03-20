# Step 11 - Real Update Group C

## 단계 대상 작업

- 에이전트 프롬프트 실제 수정
- `TestAgent` 2모드 구조 반영
- `CodeAgent`, `ValidatorAgent`, `PMAgent`를 새 템플릿/워크플로우와 정렬

## 작업 진행 계획

- `TestAgent.txt`를 `Design Mode`와 `Execution Mode` 중심으로 재작성한다.
- `CodeAgent.txt`에 `TestDesignArtifact` 입력과 테스트 설계 반영 의무를 추가한다.
- `ValidatorAgent.txt`에 `TEST-DESIGN`, `TEST-EXECUTION` 전용 판정 지침을 반영한다.
- `PMAgent.txt`에 새로운 artifact completeness 기준과 handoff 규칙을 반영한다.

## 기대 효과

- 새 워크플로우가 실제 실행 프롬프트 수준에서도 동작 가능해진다.
- 템플릿과 프롬프트 사이의 정합성이 맞춰진다.
- 이후 시스템 부트스트랩 및 보고서 템플릿 수정이 더 쉬워진다.

## 예상 변경 범위

- `open-sdlc-engine/prompts/agent/TestAgent.txt`
- `open-sdlc-engine/prompts/agent/CodeAgent.txt`
- `open-sdlc-engine/prompts/agent/ValidatorAgent.txt`
- `open-sdlc-engine/prompts/agent/PMAgent.txt`

## 작업 결과

### 수정 파일

- `open-sdlc-engine/prompts/agent/TestAgent.txt`
- `open-sdlc-engine/prompts/agent/CodeAgent.txt`
- `open-sdlc-engine/prompts/agent/ValidatorAgent.txt`
- `open-sdlc-engine/prompts/agent/PMAgent.txt`

### 반영 내용 요약

#### 1. `TestAgent.txt`

- 단일 역할 설명에서 `Design Mode`와 `Execution Mode` 2모드 구조로 재작성했다.
- `Design Mode`에서 `UseCaseModelArtifact`와 `UC Validation`을 읽고 `TestDesignArtifact`를 생성하도록 명시했다.
- `Execution Mode`에서 `UseCaseModelArtifact`, `TestDesignArtifact`, `ImplementationArtifact`, `IMPL Validation`을 읽고 `TestReportArtifact`를 생성하도록 명시했다.
- `related_test_scenario_id`, scenario coverage, evidence type, runtime evidence 같은 새 구조를 반영했다.

#### 2. `CodeAgent.txt`

- 구현 입력을 `UseCaseModelArtifact` + `TestDesignArtifact` 기반으로 확장했다.
- `TEST-DESIGN Validation`도 상위 검증 입력으로 읽도록 추가했다.
- 구현이 테스트 설계에서 요구한 preconditions, state transitions, observable outcomes를 지원해야 한다는 점을 명시했다.

#### 3. `ValidatorAgent.txt`

- `TestDesignArtifact` 검증 지침을 추가했다.
- `TestReportArtifact` 검증 지침을 `test design traceability`, `scenario execution completeness`, `evidence type consistency`, `defect quality` 중심으로 강화했다.
- `TEST-DESIGN`과 `TEST-EXECUTION`에 대한 `pass/warning/fail` decision guidance를 별도로 추가했다.

#### 4. `PMAgent.txt`

- completeness 검사 대상에 `TEST-DESIGN`, `TEST-EXECUTION`을 추가했다.
- `TEST-DESIGN` 승인 후에만 CodeAgent로 handoff하도록 명시했다.
- `TEST-EXECUTION` 실패가 구현 결함이면 CodeAgent 재작업 루프로 돌릴 수 있도록 명시했다.
- 최종 보고서 검증 항목에 test design / test execution validation status와 `TD-XX.yaml` evidence cross-check를 반영했다.

### 수정 후 검토 결과

- `TestAgent.txt`는 새 템플릿 구조와 맞게 두 모드로 분리되었다.
- `CodeAgent.txt`는 `TestDesignArtifact`를 입력으로 명확히 요구한다.
- `ValidatorAgent.txt`는 새 stage 이름과 판정 구조를 반영한다.
- `PMAgent.txt`는 새 아티팩트 세트 completeness 기준을 사용한다.

## 사용자 확인 상태

- 11단계 결과를 사용자에게 보고 후 확인 요청 예정
- 승인 시 다음 단계는 묶음 D 실제 수정으로 진행

## 다음 단계

- `Step 12 - Real Update Group D`
- 목표: 시스템 부트스트랩 프롬프트와 verification report 템플릿 실제 수정
