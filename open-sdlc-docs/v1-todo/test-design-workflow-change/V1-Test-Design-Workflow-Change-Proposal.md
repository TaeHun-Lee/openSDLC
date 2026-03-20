# OpenSDLC v1 Test Design Workflow Change Proposal

## 1. 문서 목적

이 문서는 다음 사용자 질문과 그에 대한 Codex의 답변을 출발점으로 삼아, OpenSDLC v1의 워크플로우를 어떻게 수정해 검증해볼지 더 자세히 정리한 메모다.

핵심 초점은 현재 v1의 `UC -> IMPL -> TEST` 구조가 적절한지 재검토하고, 이를 `UC -> TEST 시나리오 생성 -> IMPL -> TEST 시나리오 실행 및 검증` 구조로 분리하는 것이 더 타당한지 분석하는 데 있다.

이 문서는 v2 제안 문서와 별개로, v1에서 먼저 실험하고 검증할 수 있는 실천 가능한 변경안에 집중한다.

## 2. 사용자 질문 원문

> v1 의 워크플로우에서 "UC -> IMPL -> TEST" 과정이 맞는 걸까? "UC -> TEST 시나리오 생성 -> IMPL -> TEST 시나리오 실행 및 검증"이 맞을것 같은데

## 3. Codex 답변 요약

질문에 대한 핵심 답변은 다음과 같다.

- 현재 v1의 `UC -> IMPL -> TEST` 구조는 단순화된 구조이며, 통제력과 테스트 누락 방지 측면에서는 부족할 수 있다.
- `TEST`가 구현 이후에 한 번에 처리되면 테스트가 사실상 "사후 검증" 역할만 하게 되고, "사전 테스트 설계" 역할이 약해진다.
- 그 결과 `acceptance_criteria`만 보고 테스트를 생성하고, `main_flow`, `preconditions`, `trigger`, `observable_outcome` 같은 중요한 실행 맥락이 빠질 수 있다.
- 따라서 더 적절한 구조는 다음과 같다.

```text
UC
-> TEST Scenario / Test Design 생성
-> IMPL
-> TEST Execution / Verification
```

이 구조를 사용하면 다음 효과를 기대할 수 있다.

- 구현 전에 무엇을 검증해야 하는지가 먼저 고정된다.
- CodeAgent가 테스트 관점을 의식하며 구현하게 된다.
- TestAgent가 사후 합리화가 아니라 사전 설계 기준으로 검증할 수 있다.
- `main_flow`, `preconditions`, `trigger`, `observable_outcome`를 테스트 설계 단계에서 강제할 수 있다.

## 4. 왜 이 질문이 중요해졌는가

이 질문은 단순한 워크플로우 취향 문제가 아니다.

이번 TetrisLikeGame 사례에서 실제로 다음 문제가 발생했다.

- `UC-01-01`의 `main_flow`에는 입력 처리와 자동 낙하라는 중요한 실행 단계가 있었다.
- 하지만 `TEST-01`은 주로 `acceptance_criteria`를 기준으로 테스트를 만들었다.
- 그 결과 페이지 첫 진입 시 활성 블록 생성 여부, 입력 가능 상태의 전제조건, 시간 경과 기반 자동 낙하 같은 항목이 독립 테스트로 잡히지 않았다.
- 결국 구현상 버그가 존재했는데도 테스트는 통과한 것처럼 보였다.

즉, 현재 v1 구조는 "테스트 설계가 구현 뒤로 밀리면서 발생하는 구조적 누락"을 유발할 가능성이 있다.

## 5. 현재 v1 구조의 한계

현재 v1 관점의 기본 파이프라인은 다음처럼 이해할 수 있다.

```text
UC -> VAL -> IMPL -> VAL -> TEST -> VAL -> FB -> VAL
```

이 구조의 한계는 아래와 같다.

### 5.1 TestAgent의 책임이 두 가지로 혼합됨

현재 TestAgent는 사실상 아래 두 역할을 동시에 맡고 있다.

- 테스트 설계
- 테스트 실행 및 평가

이 두 역할을 한 단계에서 수행하면, 설계 자체의 누락을 검증 없이 넘어갈 가능성이 커진다.

### 5.2 테스트 설계의 기준이 구현물에 끌려갈 수 있음

구현 이후 테스트를 설계하면, 테스트가 "원래 요구사항을 검증하는 도구"보다 "이미 구현된 것을 설명하는 도구"가 되기 쉽다.

즉,

- 요구사항 중심 테스트가 아니라
- 구현 추종형 테스트

로 변질될 위험이 있다.

### 5.3 `acceptance_criteria` 중심 테스트로 축소될 위험

현재 구조에서는 TestAgent가 `acceptance_criteria`를 중심으로만 테스트를 작성해도 외형상 자연스럽다. 그러나 실제로는 아래 항목도 테스트 설계에 포함되어야 한다.

- `main_flow`
- `alternate_flows`
- `preconditions`
- `trigger`
- `observable_outcome`

이들이 빠지면 실행 흐름 기반 결함이 누락된다.

### 5.4 "테스트 누락" 자체를 검증하기 어려움

테스트 설계와 실행이 분리되지 않으면, Validator가 "이 테스트 리포트가 요구사항을 충분히 커버하는가"를 판정하기도 더 어려워진다.

## 6. 제안하는 v1 개정 워크플로우

v1에 먼저 반영해볼 개정안은 다음과 같다.

```text
UC
-> VAL
-> TEST-DESIGN
-> VAL
-> IMPL
-> VAL
-> TEST-EXECUTION
-> VAL
-> FB
-> VAL
```

즉, 현재 `TEST`를 두 단계로 나눈다.

- `TEST-DESIGN`: 테스트 시나리오와 커버리지 설계
- `TEST-EXECUTION`: 실제 구현 결과에 대한 실행/코드/혼합 검증

## 7. 각 단계의 역할 재정의

### 7.1 UseCaseModelArtifact (`UC`)

기존과 동일하게 요구사항을 정의하지만, 테스트 설계 단계가 뒤따르므로 아래 정보의 품질이 더 중요해진다.

- use case 분해
- acceptance criteria
- main flow
- alternate flows
- preconditions
- trigger
- observable outcome

### 7.2 Test Design Artifact (`TEST-DESIGN`, 신규)

이 단계는 구현 전에 생성된다.

포함해야 할 내용 예시는 다음과 같다.

- use case별 테스트 시나리오 목록
- acceptance criteria coverage
- main flow coverage
- precondition coverage
- trigger coverage
- observable outcome coverage
- expected evidence type
- runtime verification required 여부
- code-only verification allowed 여부

이 산출물은 이후 CodeAgent와 Test Execution 단계 모두의 기준점이 된다.

### 7.3 ImplementationArtifact (`IMPL`)

CodeAgent는 이제 단순히 UC만 보지 않고, 승인된 TEST-DESIGN까지 참조해 구현해야 한다.

즉 CodeAgent는 다음을 의식해야 한다.

- 어떤 테스트 시나리오가 예정되어 있는가
- 어떤 전제조건이 반드시 충족되어야 하는가
- 어떤 동작은 코드 존재만으로는 통과될 수 없는가

### 7.4 Test Execution / Verification (`TEST-EXECUTION`)

이 단계는 더 이상 테스트 설계를 새로 만드는 단계가 아니다.

대신 다음 역할을 수행한다.

- TEST-DESIGN에 정의된 시나리오 실행
- 구현과 테스트 설계 간 불일치 식별
- 실제 evidence 수집
- defect/improvement 판단
- satisfaction score 산정

즉 "무엇을 테스트할지"가 아니라 "설계된 테스트를 수행했을 때 무슨 결과가 나왔는지"를 기록하는 단계가 된다.

## 8. 왜 이 구조가 더 나은가

### 8.1 테스트 설계가 구현 전에 고정된다

구현 전에 테스트 시나리오가 승인되면, 테스트가 구현에 종속되지 않고 요구사항에 종속된다.

### 8.2 TestAgent의 누락을 Validator가 더 잘 잡을 수 있다

Validator는 TEST-DESIGN 단계에서 다음을 직접 검사할 수 있다.

- `main_flow` 누락 여부
- `preconditions` 누락 여부
- 시간 경과 기반 시나리오 누락 여부
- 단순 AC 매핑만 하고 있는지 여부

### 8.3 CodeAgent의 자의적 구현을 줄일 수 있다

CodeAgent는 "나중에 테스트가 어떻게 검증할지"가 이미 정해진 상태에서 구현하므로, 임의 해석이 줄어든다.

### 8.4 실행 기반 문제를 더 잘 드러낼 수 있다

이번 사례의 핵심은 다음이었다.

- 입력 이벤트 바인딩 자체는 존재했다.
- 하지만 활성 블록이 없어 사용자 체감상 입력이 먹지 않았다.
- 자동 낙하 루프도 시간 기반 테스트가 없어서 놓쳤다.

이런 문제는 TEST-DESIGN이 있다면 더 쉽게 드러난다. 왜냐하면 설계 단계에서 이미

- "페이지 첫 진입 시 활성 블록 존재"
- "시간 경과 후 자동 하강"

같은 시나리오를 따로 적어야 하기 때문이다.

## 9. v1에 반영할 파일 변경 제안

이 실험을 v1에 반영하려면 최소한 아래 파일들이 바뀌어야 한다.

### 9.1 워크플로우 정의 문서

- `open-sdlc-engine/core-concepts/workflow.md`
- `open-sdlc-engine/core-concepts/core-concept.md`

반영 내용:

- 전체 파이프라인에 `TEST-DESIGN` 단계를 추가
- `TEST` 단계를 `TEST-DESIGN`과 `TEST-EXECUTION`으로 분리

### 9.2 에이전트 정의 문서

- `open-sdlc-engine/core-concepts/agent-definitions.md`

반영 방향 두 가지:

1. 기존 TestAgent를 두 역할로 분리
   - `TestDesignAgent`
   - `TestAgent`

2. 기존 TestAgent를 유지하되 두 단계 모드로 나누기
   - TestAgent(Design Mode)
   - TestAgent(Execution Mode)

v1에서는 문서 변경을 최소화하려면 2번이 더 현실적일 수 있다.

### 9.3 프롬프트 파일

- `open-sdlc-engine/prompts/agent/TestAgent.txt`

변경 방향:

- 테스트 설계 모드와 실행 검증 모드를 분리
- `acceptance_criteria`뿐 아니라 `main_flow`, `preconditions`, `trigger`, `observable_outcome`를 반드시 읽고 테스트 설계에 반영하도록 강화

추가 가능 파일:

- `open-sdlc-engine/prompts/agent/TestDesignAgent.txt`

### 9.4 템플릿 파일

기존:

- `open-sdlc-engine/templates/artifacts/TestReportArtifact.yaml`

신규 제안:

- `open-sdlc-engine/templates/artifacts/TestDesignArtifact.yaml`

### 9.5 Validator 규칙

- `open-sdlc-engine/prompts/agent/ValidatorAgent.txt`
- `open-sdlc-engine/templates/artifacts/ValidationReportArtifact.yaml`

반영 내용:

- `TEST-DESIGN` 단계 전용 required checks 추가
- `main_flow_coverage`
- `precondition_coverage`
- `trigger_coverage`
- `observable_outcome_coverage`

## 10. 신규 아티팩트 초안 방향

`TestDesignArtifact`는 대략 아래 필드를 가질 수 있다.

```yaml
artifact_id: "TD-{{id}}"
artifact_type: "TestDesignArtifact"
iteration: {{iteration}}
created_by: "TestAgent"
created_at: "{{timestamp}}"
source_artifact_ids:
  - "UC-{{source_usecase_id}}"
status: "draft"
summary: "{{this_artifact_summary}}"
instructions_for_next_agent: |
  TestDesignArtifact를 검증하라.

test_design_scope:
  use_case_ids:
    - "UC-{{source_usecase_id}}-01"

coverage_plan:
  acceptance_criteria:
    - "{{ac_1}}"
  main_flow_steps:
    - "{{main_flow_step_1}}"
  preconditions:
    - "{{precondition_1}}"
  triggers:
    - "{{trigger_1}}"
  observable_outcomes:
    - "{{observable_outcome_1}}"

test_scenarios:
  - scenario_id: "TS-{{id}}-01"
    related_use_case_id: "UC-{{source_usecase_id}}-01"
    purpose: "{{scenario_purpose}}"
    setup: "{{setup}}"
    action: "{{action}}"
    expected_result: "{{expected_result}}"
    evidence_type: "{{runtime_or_code_or_mixed}}"

coverage_summary:
  uncovered_items: []
```

핵심은 이 아티팩트가 "무엇을 테스트할지"를 구현 전에 고정하는 역할을 해야 한다는 점이다.

## 11. 검증 방안

이 변경이 실제로 유효한지 검증하려면 단순 문서 변경으로 끝내면 안 된다.

다음 방식으로 검증하는 것이 좋다.

### 11.1 회귀 대상 선정

이미 문제가 드러난 사례를 기준으로 검증한다.

추천 대상:

- `workspace/TetrisLikeGame` 사례

왜냐하면 이 사례는

- 입력 가능 전제조건 누락
- 자동 낙하 시간 흐름 누락
- AC 중심 테스트 한계

를 모두 보여주기 때문이다.

### 11.2 비교 실험

동일 요구사항에 대해 아래 두 방식으로 각각 아티팩트를 만들어본다.

1. 기존 v1 방식
   - `UC -> IMPL -> TEST`

2. 개정 실험 방식
   - `UC -> TEST-DESIGN -> IMPL -> TEST-EXECUTION`

비교 항목:

- `main_flow` 커버리지 차이
- `preconditions` 커버리지 차이
- 시간 기반 시나리오 누락 여부
- Validator의 누락 탐지율
- 테스트 설계 품질 차이

### 11.3 성공 기준

다음이 충족되면 실험이 유효하다고 볼 수 있다.

- 기존 방식에서 누락된 `main_flow` 단계가 TEST-DESIGN에 명시된다
- Test Execution이 해당 시나리오를 실제로 평가한다
- Validator가 테스트 누락을 더 쉽게 검출한다
- CodeAgent가 구현 전에 테스트 설계 기준을 참조하게 된다

## 12. 예상 효과

이 변경을 v1에 반영해 검증하면 다음 효과를 기대할 수 있다.

- 테스트 설계 누락이 구조적으로 줄어든다
- 구현이 요구사항뿐 아니라 테스트 기준에도 묶인다
- Validator가 테스트 부실을 더 잘 차단한다
- `main_flow`, `preconditions`, `trigger` 기반 결함을 더 일찍 발견할 수 있다
- v2 정책 엔진 설계 전에, 테스트 워크플로우 개선만으로 얼마나 통제력이 올라가는지 실측할 수 있다

## 13. 예상 리스크

이 변경은 장점만 있는 것은 아니다.

### 13.1 파이프라인 길이 증가

단계가 하나 더 늘어나므로 문서량과 검증량이 증가한다.

### 13.2 TestAgent 책임 재설계 필요

설계와 실행을 나누면서 프롬프트, 템플릿, Validator 기준도 함께 바뀌어야 한다.

### 13.3 운영 복잡도 증가

v1을 실험적으로 바꾸는 동안 기존 문서와 신규 문서가 혼재할 수 있다.

하지만 이 리스크는 "구조적 테스트 누락 방지"라는 기대 효과에 비하면 충분히 감당할 수 있는 수준으로 보인다.

## 14. Codex 제안 결론

질문하신 방향은 타당하다.

OpenSDLC v1의 현재 구조인 `UC -> IMPL -> TEST`는 단순하고 운영은 쉬울 수 있지만, 테스트 설계가 구현 이후로 밀리면서 중요한 실행 시나리오를 놓칠 위험이 크다.

따라서 v1에 먼저 아래 구조를 실험적으로 반영해 검증해보는 것이 좋다.

```text
UC -> VAL -> TEST-DESIGN -> VAL -> IMPL -> VAL -> TEST-EXECUTION -> VAL -> FB -> VAL
```

이 실험 결과가 좋다면,

- v2 proposal 문서에 있던 테스트 통제 강화 방향
- validator blocking rules
- artifact schema 확장

의 상당 부분을 더 자신 있게 구체화할 수 있다.

즉, 이 변경은 단순한 워크플로우 미세 조정이 아니라, OpenSDLC가 "설명 중심 검증"에서 "설계-실행 분리형 검증"으로 진화할 수 있는 중요한 실험이 된다.
