# Step 02 - Workflow Draft

## 단계 대상 작업

- `TEST-DESIGN`과 `TEST-EXECUTION`을 포함한 개정 워크플로우 초안 정리
- 신규 단계의 handoff와 validation gate 위치 정의
- Test 관련 에이전트 구조 옵션 정리

## 작업 진행 계획

- 기존 `UC -> VAL -> IMPL -> VAL -> TEST -> VAL -> FB -> VAL` 구조를 기준으로 개정 초안을 설계한다.
- 제안 문서의 방향과 현재 v1 문서 구조를 맞춰서 최소 변경 가능한 파이프라인을 도출한다.
- 단계별 입력, 출력, 다음 handoff 대상을 텍스트로 정리한다.
- `TestAgent 분리`와 `TestAgent 2모드` 옵션을 비교하고 현 시점 권장안을 제시한다.

## 기대 효과

- 이후 아티팩트/프롬프트/Validator 변경 작업이 흔들리지 않게 된다.
- 테스트 설계와 테스트 실행의 역할 구분이 명확해진다.
- 실제 문서 반영 전에 구조상 모호함을 줄일 수 있다.

## 예상 변경 범위

- 본 단계는 워크플로우 초안과 의사결정 메모 정리 중심이다.
- 실제 운영 문서 본문은 아직 수정하지 않는다.
- 작업 이력 문서만 신규 생성한다.

## 작업 결과

### 권장 개정 파이프라인 초안

```text
User
-> PMAgent
-> ReqAgent
-> ValidatorAgent (UC)
-> TestAgent [Design Mode]
-> ValidatorAgent (TEST-DESIGN)
-> CodeAgent
-> ValidatorAgent (IMPL)
-> TestAgent [Execution Mode]
-> ValidatorAgent (TEST-EXECUTION)
-> CoordAgent
-> ValidatorAgent (FB)
-> PMAgent
```

이를 기존 아티팩트 흐름 형태로 쓰면 다음과 같다.

```text
UC -> VAL -> TEST-DESIGN -> VAL -> IMPL -> VAL -> TEST-EXECUTION -> VAL -> FB -> VAL
```

### 단계별 handoff 초안

1. `ReqAgent`
   - 입력: User Story
   - 출력: `UseCaseModelArtifact`
   - 다음 단계: `ValidatorAgent`

2. `ValidatorAgent` (`UC`)
   - 입력: `UseCaseModelArtifact`
   - 출력: `ValidationReportArtifact`
   - 통과 시 다음 단계: `TestAgent [Design Mode]`

3. `TestAgent [Design Mode]`
   - 입력: 승인된 `UseCaseModelArtifact`
   - 출력: `TestDesignArtifact` 신규 제안
   - 역할: 구현 전에 테스트 시나리오, 커버리지, 예상 evidence 기준 고정
   - 다음 단계: `ValidatorAgent`

4. `ValidatorAgent` (`TEST-DESIGN`)
   - 입력: `TestDesignArtifact`
   - 출력: `ValidationReportArtifact`
   - 통과 시 다음 단계: `CodeAgent`

5. `CodeAgent`
   - 입력: 승인된 `UseCaseModelArtifact`, 승인된 `TestDesignArtifact`
   - 출력: `ImplementationArtifact`
   - 역할: 요구사항뿐 아니라 사전 승인된 테스트 설계 기준까지 반영한 구현
   - 다음 단계: `ValidatorAgent`

6. `ValidatorAgent` (`IMPL`)
   - 입력: `ImplementationArtifact`
   - 출력: `ValidationReportArtifact`
   - 통과 시 다음 단계: `TestAgent [Execution Mode]`

7. `TestAgent [Execution Mode]`
   - 입력: `UseCaseModelArtifact`, `TestDesignArtifact`, `ImplementationArtifact`
   - 출력: `TestReportArtifact`
   - 역할: 미리 설계된 테스트를 실행하고 실제 evidence, defect, score를 기록
   - 다음 단계: `ValidatorAgent`

8. `ValidatorAgent` (`TEST-EXECUTION`)
   - 입력: `TestReportArtifact`
   - 출력: `ValidationReportArtifact`
   - 통과 시 다음 단계: `CoordAgent`

9. `CoordAgent`
   - 입력: `TestReportArtifact`
   - 출력: `FeedbackArtifact`
   - 다음 단계: `ValidatorAgent`

10. `ValidatorAgent` (`FB`)
    - 입력: `FeedbackArtifact`
    - 출력: `ValidationReportArtifact`
    - 통과 시 다음 단계: `PMAgent`

11. `PMAgent`
    - 입력: 전체 iteration artifact set
    - 출력: `verification_report.md`
    - 역할: 종료 권고 또는 다음 iteration 사용자 확인

### 핵심 구조 변화

- `TEST`가 더 이상 단일 단계가 아니다.
- `무엇을 테스트할지`는 `TEST-DESIGN`에서 먼저 고정된다.
- `무엇이 실제로 통과/실패했는지`는 `TEST-EXECUTION`에서 별도로 기록된다.
- `CodeAgent`는 이제 `UC`뿐 아니라 승인된 테스트 설계도 입력으로 받아야 한다.

### 에이전트 구조 옵션 비교

#### 옵션 A - `TestDesignAgent` 신규 도입

장점:
- 역할 분리가 가장 명확하다.
- 문서상 책임 구분이 분명하다.

단점:
- 에이전트 종류, 프롬프트, 정의 문서 변경 폭이 커진다.
- v1 실험치고는 구조 변경이 커질 수 있다.

#### 옵션 B - 기존 `TestAgent`를 Design/Execution 2모드로 운영

장점:
- 문서 변경 범위를 상대적으로 줄일 수 있다.
- 기존 v1 구조를 크게 깨지 않으면서 실험 가능하다.

단점:
- 한 에이전트 내부에서 역할 설명을 더 정교하게 나눠야 한다.
- 프롬프트 설계가 부실하면 다시 역할 혼합 위험이 생긴다.

### 현 단계 권장안

- v1 실험 단계에서는 **옵션 B**, 즉 `기존 TestAgent를 Design/Execution 2모드로 운영`하는 방식이 가장 현실적이다.
- 이유는 다음과 같다.
  - 현재 목표는 v1 전체 재설계가 아니라 테스트 누락 감소 효과를 빠르게 검증하는 것이다.
  - 신규 에이전트 추가보다 `TestDesignArtifact`와 validator 기준 추가가 핵심 효과에 더 직접적이다.
  - 문서 변경 범위를 줄인 상태로 샘플 검증까지 빠르게 이어갈 수 있다.

### 예상 영향

- `workflow.md`, `core-concept.md`, `agent-definitions.md`는 파이프라인과 역할 설명을 수정해야 한다.
- `CodeAgent` 입력 설명도 이후 단계에서 수정 가능성이 높다.
- `ValidationReportArtifact`는 `TEST-DESIGN`, `TEST-EXECUTION`을 구분할 수 있어야 한다.

## 사용자 확인 상태

- 2단계 결과를 사용자에게 보고 후 확인 요청 예정
- 승인 시 3단계 `신규/변경 아티팩트 구조 확정`으로 진행

## 다음 단계

- `Step 03 - Artifact Structure Draft`
- 목표: `TestDesignArtifact` 초안과 `TestReportArtifact`/`ValidationReportArtifact` 변경 방향 정리
