# Step 09 - Real Update Group A

## 단계 대상 작업

- 워크플로우/개념 문서 실제 수정
- 새 공식 파이프라인과 `TestAgent` 2모드 구조 반영
- 문서 간 용어와 순서 정합성 확보

## 작업 진행 계획

- `workflow.md`, `core-concept.md`, `agent-definitions.md`를 실제 수정한다.
- `UC -> VAL -> TEST-DESIGN -> VAL -> IMPL -> VAL -> TEST-EXECUTION -> VAL -> FB -> VAL` 구조를 공식 파이프라인으로 반영한다.
- `TestAgent`를 `Design Mode`, `Execution Mode`로 설명하고, 관련 연쇄 영향(`CodeAgent`, `ValidatorAgent`, `PMAgent`, `CoordAgent`)을 개념 문서에 함께 반영한다.

## 기대 효과

- 운영 문서 최상위 골격이 새 구조와 맞춰진다.
- 이후 템플릿과 프롬프트를 안정적으로 수정할 수 있다.
- 용어 혼용으로 인한 정합성 문제를 줄일 수 있다.

## 예상 변경 범위

- `open-sdlc-engine/core-concepts/workflow.md`
- `open-sdlc-engine/core-concepts/core-concept.md`
- `open-sdlc-engine/core-concepts/agent-definitions.md`

## 작업 결과

### 수정 파일

- `open-sdlc-engine/core-concepts/workflow.md`
- `open-sdlc-engine/core-concepts/core-concept.md`
- `open-sdlc-engine/core-concepts/agent-definitions.md`

### 반영 내용 요약

#### 1. `workflow.md`

- 전체 실행 프로세스를 아래 순서로 변경했다.

```text
User
-> PMAgent
-> ReqAgent
-> ValidatorAgent (UC)
-> TestAgent (Design Mode)
-> ValidatorAgent (TEST-DESIGN)
-> CodeAgent
-> ValidatorAgent (IMPL)
-> TestAgent (Execution Mode)
-> ValidatorAgent (TEST-EXECUTION)
-> CoordAgent
-> ValidatorAgent (FB)
-> PMAgent
```

- 자동화 규칙에 아래 개념을 추가했다.
  - `TEST-DESIGN Pass` 이후에만 구현 시작
  - `TEST-EXECUTION Fail`이 구현 결함과 연결되면 CodeAgent 재작업 가능

- 품질 게이트에 `테스트 설계 선행 원칙`을 명시했다.

#### 2. `core-concept.md`

- `Role-Based Agent Orchestration`에 `TestAgent` 2모드 구조를 반영했다.
- `Full Traceability`에 `TEST-DESIGN`, `TEST-EXECUTION` 추적성을 추가했다.
- `No-Shortcut Principle`의 공식 파이프라인을 새 구조로 변경했다.
- 핵심 아티팩트 파이프라인에 `TestDesignArtifact` 단계와 `TestAgent (Execution Mode)` 단계를 반영했다.

#### 3. `agent-definitions.md`

- `PMAgent`에 `TEST-DESIGN`, `TEST-EXECUTION` 포함 artifact completeness 통제 책임을 추가했다.
- `ValidatorAgent`에 `TestDesignArtifact`와 `TestReportArtifact`를 서로 다른 품질 게이트로 검증한다는 설명을 추가했다.
- `CodeAgent` 입력 기준을 `UseCaseModelArtifact` + `TestDesignArtifact`로 확장했다.
- `TestAgent`를 `Design Mode`, `Execution Mode` 2모드 구조로 재정의했다.
- `CoordAgent` 입력 설명을 `TEST-EXECUTION` 결과 기준으로 정렬했다.

### 수정 후 검토 결과

- 세 문서 모두 `TEST-DESIGN`, `TEST-EXECUTION` 용어를 일관되게 사용한다.
- 문서 간 공식 파이프라인 순서가 동일하다.
- `TestAgent` 2모드 구조가 세 문서에서 모순 없이 반영됐다.

## 사용자 확인 상태

- 9단계 결과를 사용자에게 보고 후 확인 요청 예정
- 승인 시 다음 단계는 묶음 B 실제 수정으로 진행

## 다음 단계

- `Step 10 - Real Update Group B`
- 목표: `TestDesignArtifact` 신규 추가 및 관련 템플릿 실제 수정
