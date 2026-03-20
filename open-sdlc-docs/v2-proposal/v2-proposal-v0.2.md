# OpenSDLC v2 Proposal v0.2

## 1. 문서 목적

이 문서는 `v2-proposal-v0.1.md` 이후 반영된 실제 개선사항을 기준으로 OpenSDLC v2의 초점을 재정렬한 마이너 버전 제안서다.

v0.1이 "왜 v2가 필요한가"에 집중했다면, v0.2는 다음 질문에 답한다.

- v1에 이미 반영된 개선은 무엇인가
- 그 개선으로 해결된 문제와 아직 남은 문제는 무엇인가
- v2는 이제 어디에 집중해야 하는가

## 2. v0.1 이후 v1에 실제 반영된 개선

최근 v1에는 다음 변화가 실제로 반영되었다.

### 2.1 테스트 워크플로우 분리

기존 단일 `TEST` 단계는 아래 구조로 재정렬되었다.

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
-> verification_report.md
```

이로 인해 구현 전에 테스트 시나리오가 고정되고, 구현 후에는 해당 설계를 기준으로 실행 검증이 수행되는 구조가 마련되었다.

### 2.2 Validator 단계별 강화

`ValidatorAgent`와 `ValidationReportArtifact`는 이제 `TEST-DESIGN`과 `TEST-EXECUTION`을 별도 단계로 다룬다.

반영된 주요 체크:

- `acceptance_criteria_coverage`
- `main_flow_coverage`
- `precondition_coverage`
- `trigger_coverage`
- `observable_outcome_coverage`
- `scenario_execution_completeness`
- `evidence_quality`
- `score_consistency`

### 2.3 Sequential Single-Agent Execution 강화

OpenSDLC는 이제 단순 서술 규칙이 아니라 실제 실행 잠금 규칙으로 정리되었다.

- 특정 시점에 오직 하나의 에이전트만 활성화
- 병렬 툴 실행 금지
- 다중 단계 묶음 실행 금지
- handoff 전 아티팩트와 validator 결과 확인 의무

### 2.4 PMAgent 사용자 인터랙션 경계 강화

사용자 입력/승인 요청은 `PMAgent`만 수행하도록 경계가 더 명확해졌다.

### 2.5 문서-프롬프트-템플릿 정렬

헌법, 엔진 개념, 프롬프트, 템플릿, verification report 구조가 최신 파이프라인에 맞춰 상당 부분 정렬되었다.

### 2.6 실제 workspace 실행 검증

`workspace/BlogWebApp/` 예시를 통해 다음이 실제로 검증되었다.

- Iteration 01: 기본 CRUD + 2단 레이아웃 + 시간 추적
- Iteration 02: 수정 일시 가시성 보강 + 콤팩트 헤더 + 테마 적용

즉, v1은 단순 제안 수준이 아니라 실제 실행 가능한 파이프라인 구조를 이미 확보한 상태다.

## 3. v1 개선으로 해결된 문제

위 변화로 다음 영역은 v0.1 당시보다 분명히 나아졌다.

### 3.1 테스트 설계 누락 문제 완화
- 구현 전에 `TEST-DESIGN`이 승인되어야 하므로, 테스트 설계가 구현 이후 사후 합리화로 밀리는 문제가 줄었다.

### 3.2 main flow / precondition 누락 방지 강화
- 테스트 설계와 validator 체크가 AC 중심에서 flow/state 맥락까지 확장되었다.

### 3.3 handoff 통제력 상승
- `CodeAgent`는 승인된 `UC`와 승인된 `TEST-DESIGN` 모두를 입력으로 받게 되었다.

### 3.4 실행 순서 위반 위험 감소
- 순차 단일 실행 규칙이 실제 tool execution guardrail로 강화되었다.

### 3.5 아티팩트 추적성 강화
- `UC -> TEST-DESIGN -> IMPL -> TEST-EXECUTION -> FB` 체인이 더 명확해졌다.

## 4. 그럼에도 남아 있는 v2 핵심 문제

v1이 강해졌지만, v2가 여전히 필요한 이유는 다음과 같다.

### 4.1 여전히 자연어 규정 중심이다

많은 규칙이 문서와 프롬프트에 더 잘 정리되었지만, 중요한 통제는 아직도 자연어 해석에 크게 의존한다.

### 4.2 diff 중심 승인 통제가 부족하다

현재도 validator는 산출물과 evidence를 더 잘 검증하지만, "실제 diff가 승인된 요구와 어떤 의미로 연결되는가"를 기계적으로 분류하는 정책 계층은 없다.

### 4.3 UX 의미 변경 차단은 아직 선언적이다

무단 UX 의미 변경, 상태 전이 변경, interaction model 변경은 v1에서 더 잘 경계되지만, 아직 별도 정책 엔진이 diff를 직접 분석해 자동 차단하지는 않는다.

### 4.4 approval-sensitive change 체계가 부족하다

어떤 변경이 단순 내부 수정이고 어떤 변경이 사용자 승인 필수인지에 대한 결정이 아직 충분히 데이터화되지 않았다.

### 4.5 evidence confidence 구분이 더 필요하다

현재 v1은 runtime evidence와 code evidence를 더 잘 구분하지만, v2 수준에서는 `verified`, `partially verified`, `inferred only` 같은 더 정교한 신뢰도 계층이 필요하다.

### 4.6 메타 컴플라이언스 감사가 부족하다

"이번 iteration이 OpenSDLC 자체를 얼마나 잘 지켰는가"를 별도의 메타 감사 아티팩트나 정책으로 다루는 구조는 아직 약하다.

## 5. v2의 초점 재정의

v2는 더 이상 단순히 `TEST-DESIGN`을 도입하는 버전이 아니다. 그 일은 상당 부분 v1 개선으로 이미 진행되었다.

따라서 v2의 핵심 초점은 다음으로 재정의되어야 한다.

### 5.1 Prompt-Centric Control -> Policy-Centric Control
- 자연어 설명보다 정책 파일과 검사기 중심 구조로 이동

### 5.2 Artifact Validation -> Diff Governance
- 산출물 문서 검증을 넘어서 실제 diff와 사용자 가시 변경을 중심으로 통제

### 5.3 Approval Semantics Formalization
- 승인 민감 변경군을 정책 데이터로 명시

### 5.4 Semantic UX Guard
- 버튼 의미, 화면 기본 행동, 상태 전이, 사용자 메시지 변화 감지

### 5.5 Meta-Compliance Auditing
- OpenSDLC 프로세스 위반 자체를 별도 감사 대상으로 다룸

## 6. v2 핵심 아키텍처 제안 v0.2

### 6.1 Policy Engine 계층 도입

예상 구조:

```text
open-sdlc-engine/policies/
  change-classes.yaml
  approval-required-rules.yaml
  semantic-ux-rules.yaml
  validator-blocking-rules.yaml
  evidence-confidence-rules.yaml
```

여기서 변경은 최소 아래처럼 분류한다.

- `safe-internal-fix`
- `behavior-change`
- `ux-meaning-change`
- `scope-expansion`
- `schema-change`
- `security-sensitive-change`

### 6.2 Requirement-Diff Mapper

v2에서는 모든 의미 있는 변경이 어느 `UC` / `FB` / 승인 입력과 연결되는지 기계적으로 매핑되어야 한다.

매핑 실패 시 기본 정책:

- `warning`
  - 영향이 작고 사용자 가시성이 낮은 경우
- `fail`
  - 승인 민감 변경군이거나 의미 변화 가능성이 있는 경우

### 6.3 Semantic UX Guard

자동 감지 대상 예시:

- 버튼 명칭과 의미 변경
- 화면 기본 시작 방식 변경
- 상태 전이 규칙 변경
- 사용자 메시지 의미 변화
- 사용자 상호작용 모델 변경

### 6.4 Approval Gate Formalization

아래 변경은 명시적 승인 없이는 진행할 수 없어야 한다.

- UX 의미 변화
- interaction model 변화
- 상태 전이 변화
- 범위 외 기능 추가
- 데이터 구조 의미 변경
- 보안/권한 정책 변화

### 6.5 Evidence Confidence Layer

검증 결과는 다음 계층을 명시적으로 가져야 한다.

- `runtime-evidence-verified`
- `code-evidence-verified`
- `mixed-verified`
- `inferred-only`

특히 `inferred-only` 상태에서는 높은 만족도와 완료 권고가 제한되어야 한다.

### 6.6 Meta Compliance Report

새로운 보고/아티팩트 후보:

- `ProcessComplianceReportArtifact`
  - iteration 동안 OpenSDLC 위반이 있었는지
  - 병렬 실행 위반이 있었는지
  - handoff 전 validator gate 누락이 있었는지
  - 승인 민감 변경이 무단 통과했는지

## 7. 아티팩트 확장 제안

### 7.1 UseCaseModelArtifact

추가 후보:

- `protected_semantics`
- `approval_sensitive_elements`
- `interaction_model`
- `initial_state_requirements`

### 7.2 ImplementationArtifact

추가 후보:

- `change_classification`
- `user_visible_changes`
- `approval_required_changes`
- `requirement_diff_mapping`

### 7.3 TestReportArtifact

추가 후보:

- `runtime_evidence_status`
- `coverage_confidence`
- `missed_test_risk`
- `semantic_regression_checks`

### 7.4 ValidationReportArtifact

추가 후보:

- `unauthorized_change_detection`
- `semantic_change_detection`
- `approval_gate_result`
- `evidence_confidence`
- `policy_rule_hits`

## 8. 단계별 v2 로드맵 재정렬

### Phase 1. Policy Schema 정의
- 변경 클래스
- 승인 민감 변경군
- semantic UX 금지 객체
- evidence confidence 규칙

### Phase 2. Diff Governance 설계
- Requirement-Diff Mapper
- Change Impact Scanner
- Semantic UX Guard

### Phase 3. Validator v2 구현
- 정책 파일 읽기
- diff 기반 rule hit 생성
- fail-closed 판정 체계

### Phase 4. Artifact Schema v2 확장
- UC / IMPL / TEST / VAL 필드 확장

### Phase 5. Meta Compliance Layer 구축
- 프로세스 위반 보고
- 승인 게이트 위반 보고
- iteration-level compliance scoring

## 9. 성공 지표 v0.2

v2의 성공은 단순히 문서가 많아지는 것이 아니다. 다음 지표가 개선되어야 한다.

- 승인 없는 의미 변경 통과 건수 `0`
- requirement-diff 매핑 실패 건수 감소
- `inferred-only` 상태의 완료 권고 비율 감소
- semantic UX regression 탐지율 증가
- OpenSDLC 프로세스 위반 자동 감지율 증가

## 10. 결론

v0.1 시점의 v2는 "자연어 규정만으로는 부족하니 정책 엔진이 필요하다"는 문제 제기였다.

v0.2 시점의 v2는 그보다 한 단계 더 구체적이다.

- 테스트 설계 선행 구조는 상당 부분 v1에 이미 흡수되었다.
- 순차 실행 잠금, validator 단계 분리, workspace 기반 실행 검증도 강화되었다.
- 따라서 v2의 본질은 이제 `테스트 워크플로우 개선`이 아니라 `정책 기반 diff 통제와 승인 민감 변경 차단`으로 이동해야 한다.

한 줄 요약:

`OpenSDLC v2는 TEST-DESIGN 도입 버전이 아니라, policy-driven change governance 버전이어야 한다.`

## 11. v0.1 대비 차이 요약

- v1에 이미 반영된 개선사항을 명시적으로 인정했다.
- `TEST-DESIGN` 도입을 v2 핵심에서 제외하고, v2 초점을 `policy engine`, `diff governance`, `semantic UX guard`, `approval gate formalization`으로 재정의했다.
- 실제 workspace 실행 결과를 반영해 v2가 해결해야 할 남은 문제를 더 좁고 구체적으로 정리했다.

## 12. v0.2 심층 검토 결과

이 버전에 대해 추가 검토한 결과, 방향성은 타당하지만 다음 보완점이 확인되었다.

### 12.1 적합성 평가

`v0.2`는 LLM 기반 AI 에이전트를 위한 제안으로서 방향은 적합하다. 특히 `TEST-DESIGN` 선행, validator 단계 분리, 순차 실행 잠금 같은 문제는 이미 v1에 상당 부분 흡수되었기 때문에, v2의 초점을 `policy-driven change governance`로 옮긴 것은 논리적으로 맞다.

다만 이 적합성은 아래 조건이 충족될 때에만 의미가 크다.

- 정책 판정 로직이 단순 프롬프트 문구가 아니라 결정론적 검사기로 구현될 것
- diff 분류와 승인 게이트가 실제 파일 변경을 기준으로 작동할 것
- semantic UX 감지가 정적 규칙만이 아니라 런타임 상호작용 관찰까지 포함할 것

### 12.2 기대 개선 효과 평가

v1 대비 다음 개선은 현실적으로 기대할 수 있다.

- 승인 민감 변경의 가시성 향상
- 요구사항 외 변경 탐지율 향상
- evidence 신뢰도 표기의 명확화
- OpenSDLC 프로세스 위반에 대한 별도 감사 강화

그러나 아래는 여전히 과제로 남는다.

- 의미 변화 감지를 일반적인 UI/UX 전 영역에서 자동화하는 것
- 모든 diff를 `UC` / `FB` / 승인 입력과 안정적으로 매핑하는 것
- false positive 없이 `fail-closed` 운영을 유지하는 것

즉, v2는 v1보다 더 높은 통제력을 줄 수 있으나, CPU 수준의 확정성과 완전한 환각 배제를 달성하는 제안으로 이해하면 과대평가다.

### 12.3 핵심 검토 의견

#### 12.3.1 Prompt-Centric -> Policy-Centric 전환의 의미

이 전환은 에이전트를 CPU처럼 결정론적으로 만드는 것이 아니다.

대신 다음을 의미한다.

- LLM의 자유 해석 영역을 줄인다.
- 통과/차단 판정을 외부 정책 엔진과 검사기로 이동시킨다.
- 결과적으로 "최종 시스템 동작"을 더 예측 가능하게 만든다.

즉, 에이전트는 여전히 확률적이지만, 정책 엔진이 실패 조건을 더 강하게 봉쇄하는 구조가 된다.

#### 12.3.2 구현 가능성 평가

재정의된 v2의 초점은 구현 가능하다. 다만 "한 번에 완전 구현"이 아니라 아래 순서의 점진 구현이 더 현실적이다.

1. `change-classes.yaml`, `approval-required-rules.yaml` 같은 정책 스키마 정의
2. diff 스캔과 requirement-diff 매핑의 제한적 프로토타입 구현
3. validator에 `policy_rule_hits`, `approval_gate_result` 같은 실제 판정값 연결
4. semantic UX guard를 버튼/상태 전이/기본 시작 방식 같은 제한된 영역부터 적용
5. evidence confidence와 meta compliance report 추가

가장 구현 난도가 높은 부분은 일반형 `Semantic UX Guard`이며, 가장 빠르게 가치가 나는 부분은 `approval-required changes`와 `requirement_diff_mapping`이다.

## 13. 논의 진행 사항 정리

이번 검토를 통해 v0.2에 대해 다음 합의가 형성되었다.

### 13.1 이미 정리된 사항

- v2는 더 이상 `TEST-DESIGN` 도입 버전으로 보면 안 된다.
- `TEST-DESIGN` / `TEST-EXECUTION` 분리와 validator 강화는 이미 v1에 상당 부분 반영되었다.
- 따라서 v2의 본질은 `policy-driven change governance`에 있어야 한다.

### 13.2 추가로 명확해진 사항

- `Policy-Centric Control`은 에이전트 자체를 CPU처럼 만들지 않는다.
- 진짜 개선은 "LLM이 더 많은 문서를 읽는 구조"가 아니라 "정책 엔진이 먼저 판정하고 LLM은 그 결과를 소비하는 구조"에서 발생한다.
- `Requirement-Diff Mapper`, `Semantic UX Guard`, `Approval Gate Formalization`은 v2 핵심이지만, 이 셋은 모두 구현 경계와 false positive 관리 전략이 함께 설계되어야 한다.

### 13.3 현재 문서 해석 기준

따라서 이 문서는 다음 식으로 읽는 것이 가장 정확하다.

`v2-proposal-v0.2`는 "LLM을 완전히 통제하는 제안"이 아니라, "LLM이 자의적으로 행동하더라도 무단 변경이 통과하지 못하도록 바깥 계층을 강화하는 제안"이다.

## 14. 토큰 변화량 및 추산 예산표

`v2`를 실제로 구현하고 운영할 때의 토큰 소모는 대략 예측할 수 있다. 다만 수치는 구현 방식에 크게 좌우된다.

핵심 변수는 다음과 같다.

- 정책 파일을 LLM이 직접 매번 읽는가
- diff 분류와 approval gate를 코드/스크립트가 먼저 수행하는가
- semantic UX 감지를 정적 규칙으로만 하는가, 런타임 관찰까지 포함하는가
- fail-closed 구조로 인해 재작업 루프가 얼마나 자주 발생하는가

### 14.1 해석 기준

아래 예산표는 "중간 규모 1 iteration"을 기준으로 한 대략적 추산이다.

가정:

- use case 3~5개
- 코드 변경 파일 3~8개
- 일부 브라우저/테스트 evidence 포함
- 현재 v1은 이미 `UC -> VAL -> TEST-DESIGN -> VAL -> IMPL -> VAL -> TEST-EXECUTION -> VAL -> FB -> VAL -> verification_report` 구조를 사용

### 14.2 단계별 추산 예산표

| 단계 | v1 | v2 문서중심 | v2 하이브리드 | v2 정책엔진중심 |
| :--- | ---: | ---: | ---: | ---: |
| `ReqAgent` | 6k~12k | 8k~16k | 7k~13k | 6k~12k |
| `UC-VAL` | 5k~10k | 10k~20k | 7k~14k | 5k~9k |
| `TEST-DESIGN` | 8k~16k | 10k~20k | 9k~17k | 8k~15k |
| `TD-VAL` | 5k~10k | 9k~18k | 7k~13k | 5k~9k |
| `CodeAgent` | 10k~25k | 14k~32k | 11k~24k | 10k~22k |
| `IMPL-VAL` | 6k~14k | 14k~28k | 9k~18k | 6k~12k |
| `TEST-EXECUTION` | 10k~24k | 14k~30k | 11k~24k | 10k~22k |
| `TEST-VAL` | 6k~14k | 12k~24k | 8k~16k | 6k~12k |
| `CoordAgent` | 3k~8k | 4k~10k | 3k~8k | 3k~7k |
| `FB-VAL` | 3k~8k | 6k~12k | 4k~9k | 3k~7k |
| `PMAgent report` | 6k~14k | 10k~20k | 7k~14k | 6k~12k |

### 14.3 iteration 총량 추산

- `v1`: `68k ~ 155k`
- `v2 문서중심`: `111k ~ 250k`
- `v2 하이브리드`: `83k ~ 170k`
- `v2 정책엔진중심`: `68k ~ 141k`

### 14.4 배수 관점

- `v2 문서중심`: 대략 `1.6x ~ 2.3x`
- `v2 하이브리드`: 대략 `1.2x ~ 1.4x`
- `v2 정책엔진중심`: 대략 `1.0x ~ 1.2x`

### 14.5 해석

#### 14.5.1 문서중심 v2

정책 파일, approval rule, semantic rule을 매 단계 LLM이 직접 읽고 해석하면 토큰이 크게 늘어난다. 이 경우 v2는 통제력은 강화될 수 있지만 비용 효율은 떨어질 가능성이 높다.

#### 14.5.2 하이브리드 v2

diff 스캔, 변경 분류, approval gate 일부를 스크립트가 먼저 처리하고 LLM은 요약/판단 보조에 집중하면, 토큰 증가는 비교적 관리 가능한 수준으로 유지된다.

#### 14.5.3 정책엔진중심 v2

정책 판정과 evidence confidence가 대부분 결정론적 도구로 계산되고, LLM은 artifact 작성과 설명 중심으로 남는 구조라면, 토큰 증가율은 크지 않을 수 있다.

### 14.6 실무 결론

v2가 정말 `policy-centric`이라면 토큰이 반드시 폭증하지는 않는다.

하지만 v2가 "정책 문서를 더 많이 읽는 구조"가 되면, 개선 효과 대비 비용이 급격히 증가할 수 있다.

따라서 비용과 통제력의 균형을 위해서는 아래 원칙이 중요하다.

- 정책 원문 전체를 매번 넣지 말고 `rule hit 결과`만 LLM에 전달할 것
- raw diff 전체 대신 구조화된 change summary를 전달할 것
- validator 앞단에 결정론적 precheck를 둘 것
- `evidence confidence`는 가능하면 코드가 계산하고 LLM은 설명만 하게 할 것
