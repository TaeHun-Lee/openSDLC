# Test Design Workflow Change Summary

## 1. 작업 목적

이 작업 묶음은 OpenSDLC v1의 기존 테스트 워크플로우를 재검토하고, 단일 `TEST` 단계 구조를 다음 구조로 개편하는 방향을 분석하고 반영하기 위해 수행되었다.

```text
기존: UC -> IMPL -> TEST
개선: UC -> TEST-DESIGN -> IMPL -> TEST-EXECUTION
```

최종적으로는 정식 파이프라인을 아래와 같이 정렬하는 것이 목표였다.

```text
UC -> VAL -> TEST-DESIGN -> VAL -> IMPL -> VAL -> TEST-EXECUTION -> VAL -> FB -> VAL
```

## 2. 문제 인식

이 작업은 다음 문제의식에서 출발했다.

- 구현 이후에 테스트를 한 번에 설계/실행하면 테스트 설계가 구현 추종형으로 흐를 수 있다.
- `acceptance_criteria` 중심 검증으로 축소되면서 `main_flow`, `preconditions`, `trigger`, `observable_outcome`가 누락될 수 있다.
- TestAgent가 테스트 설계와 테스트 실행을 한 단계에서 동시에 처리하면 누락 자체를 validator가 잡기 어려워진다.

## 3. 수행 단계

이 폴더의 작업은 크게 다음 흐름으로 진행되었다.

1. `step-01`~`step-08`
   - 기존 v1 구조의 문제를 검토하고 개정 워크플로우 초안을 정리했다.
2. `step-09`~`step-12`
   - 공식 문서, 프롬프트, 템플릿, 검증 구조에 `TEST-DESIGN` / `TEST-EXECUTION` 분리 구조를 반영했다.
3. `step-13`~`step-14`
   - 지원 문서와 정합성을 재검토하고 최종 일관성 점검을 수행했다.
4. 후속 문서
   - 헌법-엔진 정렬 계획, validation 실행 준비, 교차 검증 리포트를 추가로 남겼다.

## 4. 주요 산출물

### 핵심 제안/계획 문서
- `V1-Test-Design-Workflow-Change-Proposal.md`
  - 왜 `TEST-DESIGN` 단계가 필요한지와 목표 구조를 설명한다.
- `V1-Test-Design-Workflow-Detailed-Plan.md`
  - 실제 반영/검증 절차를 더 상세히 정리한다.
- `V1-Constitution-Engine-Alignment-Improvement-Plan.md`
  - 헌법과 엔진 문서 간 파이프라인/용어 정렬 계획을 정리한다.
- `V1-Validation-Execution-Preparation.md`
  - 개정 구조를 실제 검증 실행으로 연결하기 위한 준비 상태를 정리한다.

### 이력 문서
- `history/step-01-baseline-review.md` ~ `history/step-14-final-consistency-review.md`
  - 초안 작성, 구조 설계, 문서 반영, 정합성 검토까지의 단계별 이력을 기록한다.

## 5. 반영된 핵심 변화

이 작업을 통해 저장소에는 다음 변화가 반영되었다.

- 공식 파이프라인이 `TEST-DESIGN`과 `TEST-EXECUTION` 분리 구조를 사용하도록 정렬되었다.
- `TestAgent`는 `Design Mode`와 `Execution Mode`로 나뉘어 해석되도록 정리되었다.
- `CodeAgent`는 승인된 `UC`뿐 아니라 승인된 `TEST-DESIGN`도 입력으로 참조하게 되었다.
- `ValidatorAgent`는 `TEST-DESIGN`과 `TEST-EXECUTION`을 별도 품질 게이트로 검증하도록 강화되었다.
- `ValidationReportArtifact`는 `validated_stage` 기준으로 `TEST-DESIGN` / `TEST-EXECUTION`을 분리해 판정할 수 있게 되었다.
- `FeedbackArtifact`와 verification report도 개정 파이프라인을 반영하도록 정리되었다.

## 6. 기대 효과

이 작업이 목표로 한 효과는 다음과 같다.

- 구현 전에 무엇을 테스트해야 하는지가 먼저 고정된다.
- CodeAgent가 테스트 설계를 의식하며 구현하게 된다.
- TestAgent가 사후 합리화가 아니라 승인된 테스트 설계 기준으로 검증하게 된다.
- `main_flow`, `preconditions`, `trigger`, `observable_outcome` 누락 가능성이 줄어든다.
- ValidatorAgent가 테스트 설계 누락과 실행 누락을 더 명확히 차단할 수 있다.

## 7. 현재 상태 요약

현재 이 작업 묶음은 단순 제안 수준을 넘어서, 문서/프롬프트/템플릿/검증 규칙에 상당 부분 반영된 상태를 정리한 결과물이다.

현재 상태를 한 줄로 요약하면 다음과 같다.

`OpenSDLC v1은 TEST-DESIGN 선행, TEST-EXECUTION 후행 구조를 공식 워크플로우로 채택하고 이를 헌법-엔진-프롬프트-템플릿 계층에 정렬하는 방향으로 정리되었다.`

## 8. 이 폴더 읽는 순서 권장

빠르게 파악하려면 아래 순서로 읽는 것을 권장한다.

1. `SUMMARY.md`
2. `V1-Test-Design-Workflow-Change-Proposal.md`
3. `V1-Test-Design-Workflow-Detailed-Plan.md`
4. `V1-Constitution-Engine-Alignment-Improvement-Plan.md`
5. `V1-Validation-Execution-Preparation.md`
6. 필요 시 `history/` 하위 단계 문서
