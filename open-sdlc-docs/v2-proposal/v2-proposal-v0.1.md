# OpenSDLC v2 Proposal

## 1. 문서 목적

이 문서는 OpenSDLC v1 운영 중 실제로 드러난 한계를 바탕으로, OpenSDLC v2의 개발 방향을 기획 수준에서 정리한 제안서다.

핵심 문제의식은 다음과 같다.

- LLM 에이전트가 다층 규정과 프롬프트를 이해하고도 특정 상황에서 자의적 해석과 조치를 수행할 수 있다.
- 자연어 기반 규칙만으로는 높은 수준의 통제와 환각 배제를 보장하기 어렵다.
- 따라서 v2는 "더 많은 규칙을 쓰는 시스템"이 아니라 "규칙 위반을 구조적으로 통과시키지 않는 시스템"으로 진화해야 한다.

## 2. 배경

OpenSDLC v1은 다음과 같은 철학 위에서 설계되었다.

- Artifact-Driven Execution
- Strict Adherence
- Full Traceability
- Role-Based Orchestration
- Validation Over Self-Assertion
- No-Shortcut Principle
- Sequential Single-Agent Execution

그러나 실제 운영 사례에서 다음 문제가 발생했다.

- 사용자의 명시적 지시 없이 UI 의미가 변경되었다.
- 에이전트가 내부 문제 해결을 명분으로 요구사항 외 변경을 허용 가능한 구현 디테일로 오판했다.
- Validator와 테스트가 모두 이를 차단하지 못했다.
- 결과적으로 규정은 존재했지만 위반을 "사후 설명"은 할 수 있어도 "사전 차단"하지는 못했다.

이 사례는 v1의 철학이 틀렸다는 뜻이 아니라, 자연어 규정 중심 제어만으로는 충분하지 않다는 뜻이다.

## 3. 문제 정의

OpenSDLC v2가 해결해야 할 핵심 문제는 아래 4가지다.

### 3.1 자연어 규정의 비결정성

LLM은 규칙을 CPU처럼 결정론적으로 집행하지 않는다. 문맥 속 우선순위를 확률적으로 추정하며, 문제 해결과 규정 준수가 충돌해 보일 때 자의적 최적화를 시도할 수 있다.

### 3.2 자기보고 신뢰 불가

에이전트가 "규정을 준수했다"고 보고해도 실제 diff나 실제 상태가 다를 수 있다. 따라서 자기 선언은 판정 근거가 될 수 없다.

### 3.3 검증의 형식성 부족

Validator가 규정 위반을 충분히 기계적으로 판정하지 못하면, 규정은 설명 문서로만 남고 강제력이 약해진다.

### 3.4 UX/기능 의미 변경의 무단 발생

사용자가 승인하지 않은 UX 의미 변경, 상태 전이 변경, 인터랙션 모델 변경은 치명적인 위반이지만, v1에서는 이를 별도의 금지 객체로 다루지 않았다.

## 4. v2 목표

OpenSDLC v2의 목표는 다음과 같다.

1. LLM 자율성에 의존하지 않고 규정 준수를 구조적으로 강제한다.
2. 요구사항 외 변경을 자동 탐지하고 차단한다.
3. 자연어 프롬프트를 기계 판정 가능한 규칙으로 최대한 내린다.
4. 자기보고보다 실제 산출물, 실제 diff, 실제 실행 결과를 우선한다.
5. "높은 수준의 통제"는 추구하되, "완전 통제 불가능성"을 전제로 설계한다.

## 5. v2 설계 원칙

### 5.1 Prompt-Only Control 금지

중요 제약은 프롬프트 문구만으로 강제하지 않는다. 반드시 별도의 검사기, 게이트, 스키마, 정책 엔진 중 하나 이상으로 강제한다.

### 5.2 Self-Assertion 배제

에이전트의 설명과 해석은 참고 정보일 뿐이며, 통과/실패 판정은 실제 파일, diff, 로그, 테스트 결과만으로 수행한다.

### 5.3 Diff-Centric Governance

규정 위반 여부는 문서가 아니라 실제 변경점으로 판단한다. "무엇이 바뀌었는가"를 중심으로 통제한다.

### 5.4 Approval-Sensitive Changes

UX 의미, 사용자 플로우, 상태 전이, 기능 범위, 데이터 스키마, 보안 정책 변경은 명시적 승인 없이는 진행할 수 없는 변경군으로 분류한다.

### 5.5 Reproducible Evidence First

Evidence는 실제 재현 가능한 형태여야 하며, 실행 기반 검증과 코드 기반 검증을 명확히 분리한다.

## 6. 핵심 아키텍처 제안

### 6.1 Constitution v2: 선언 규정에서 금지 객체 중심 규정으로 확장

헌법 계층에는 다음이 추가되어야 한다.

- `Unauthorized UX Mutation` 금지 조항
- `Unapproved Semantic Change` 금지 조항
- `Silent Assumption Upgrade` 금지 조항
- `Self-Justified Deviation` 금지 조항

예시:

- 버튼의 의미 변경
- 기본 시작 방식 변경
- 상태 전이 방식 변경
- 사용자가 요청하지 않은 안내 문구 변경
- 내부 편의 목적의 인터랙션 모델 변경

이러한 변경은 "디자인 변경"보다 넓은 범주로 다뤄져야 한다.

### 6.2 Engine v2: Policy Engine 계층 도입

`open-sdlc-engine`에 자연어 프롬프트 외 별도 정책 계층을 둔다.

구성 예시:

- `open-sdlc-engine/policies/change-classes.yaml`
- `open-sdlc-engine/policies/approval-required-rules.yaml`
- `open-sdlc-engine/policies/validator-blocking-rules.yaml`

여기서 변경을 분류한다.

- `safe-internal-fix`
- `behavior-change`
- `ux-meaning-change`
- `scope-expansion`
- `schema-change`
- `security-sensitive-change`

그리고 특정 클래스는 자동으로 `fail` 처리한다.

### 6.3 Validator v2: 설명 검증이 아닌 변경 검증으로 전환

Validator는 다음 질문을 기계적으로 수행해야 한다.

1. 실제 diff에 UX 의미 변화가 있는가
2. diff가 승인된 UC/FB 범위를 벗어나는가
3. 변경된 문자열, 버튼, 레이블, 상태명, 플로우가 사용자 승인 대상인가
4. 테스트가 `acceptance_criteria`만 확인하고 `main_flow` 전제조건을 빠뜨렸는가
5. 실행 증거 없이 pass/warning이 과도하게 낙관적인가

### 6.4 TestAgent v2: AC 중심에서 Flow+State 중심으로 확장

TestAgent는 더 이상 `acceptance_criteria`만 기준으로 케이스를 만들면 안 된다.

반드시 아래 3층을 모두 커버해야 한다.

- AC coverage
- Main flow coverage
- State/trigger/precondition coverage

필수 체크리스트 예시:

- 페이지 첫 진입 상태
- 초기화 완료 여부
- 이벤트가 연결만 됐는지, 실제로 반응 가능한 상태인지
- 시간 경과 기반 로직 존재 여부
- 런타임 전제조건 누락 여부

### 6.5 PMAgent v2: 승인 게이트를 더 공격적으로 운영

PMAgent는 다음 종류의 변경을 감지하면 즉시 중단해야 한다.

- UX 의미 변화
- 시작/종료 방식 변화
- 상태 전이 변화
- 범위 외 기능 추가
- 기존 요구사항 문맥을 바꾸는 문구 변경

즉, PMAgent는 단순 오케스트레이터가 아니라 "무단 변경 차단자" 역할을 강화해야 한다.

## 7. 필수 기능 요구사항

### 7.1 Change Impact Scanner

코드/문서 diff를 읽고 다음을 추출한다.

- 변경된 사용자 노출 문자열
- 변경된 버튼/라벨/상태 텍스트
- 변경된 이벤트 바인딩
- 변경된 초기화 시점
- 변경된 상태 전이 조건

### 7.2 Requirement-Diff Mapper

각 diff가 어느 UC/FB 항목에 대응되는지 강제 매핑한다.

매핑 실패 시:

- 자동 `warning` 또는 `fail`
- 승인 대상 변경군이면 즉시 `fail`

### 7.3 Semantic UX Guard

버튼, 라벨, 메시지, 사용자 가이드, 기본 행동 방식의 의미 변화를 감지한다.

예시 감지 대상:

- "게임 시작 / 재시작" -> "자동 시작"
- "버튼을 눌러 시작" -> "페이지 로드 시 자동 시작"
- 클릭 기반 시작 -> 자동 시작

### 7.4 Test Coverage Auditor

테스트가 아래를 모두 커버했는지 검사한다.

- `acceptance_criteria`
- `main_flow`
- `alternate_flows`
- `preconditions`
- `trigger`
- `observable_outcome`

누락 시 TestArtifact를 경고 또는 실패 처리한다.

### 7.5 Evidence Confidence Split

검증 결과를 아래로 명확히 구분한다.

- code-evidence verified
- runtime-evidence verified
- inferred only

`inferred only` 상태에서 높은 완료 점수가 나오는 것을 제한해야 한다.

## 8. 아티팩트 확장 제안

### 8.1 UseCaseModelArtifact 확장

추가 필드 제안:

- `protected_semantics`
- `approval_sensitive_elements`
- `interaction_model`
- `initial_state_requirements`

### 8.2 ImplementationArtifact 확장

추가 필드 제안:

- `change_classification`
- `user_visible_changes`
- `approval_required_changes`
- `requirement_diff_mapping`

### 8.3 TestReportArtifact 확장

추가 필드 제안:

- `main_flow_coverage`
- `precondition_coverage`
- `trigger_coverage`
- `runtime_evidence_status`
- `missed_test_risk`

### 8.4 ValidationReportArtifact 확장

추가 필드 제안:

- `unauthorized_change_detection`
- `semantic_change_detection`
- `approval_gate_result`
- `evidence_confidence`

## 9. 운영 모델 제안

### 9.1 모델을 "불완전한 작업자"로 간주

OpenSDLC v2는 LLM을 완전 신뢰 가능한 지능으로 다루지 않는다.

대신 아래처럼 다룬다.

- 지시를 수행할 수는 있지만 오판 가능성이 높음
- 자기 설명은 참고만 가능
- 실제 변경과 실제 실행 결과만 신뢰 가능
- 중요한 판단은 정책 엔진과 인간 승인으로 봉쇄

### 9.2 Fail-Closed 기본 정책

판정이 애매하면 통과시키지 않는다.

특히 아래는 `fail-closed`가 기본이어야 한다.

- UX 의미 변경 감지
- 요구사항 매핑 불가 diff
- 실행 증거 없이 과도한 pass 선언
- 테스트가 main flow를 누락한 경우

### 9.3 Human Approval Minimal but Strategic

사소한 입력을 계속 묻는 방식은 피하되, 의미 변화가 있는 순간만큼은 반드시 인간 승인으로 올린다.

## 10. 기술적 현실 인식

OpenSDLC v2는 "환각 완전 배제"를 목표로 두지 않는다. 그 목표는 현재 기술 현실상 부정확하다.

대신 다음을 현실 목표로 둔다.

- 환각과 자의성의 빈도 감소
- 위반의 조기 검출
- 위반의 자동 차단
- 사고 원인의 명확한 추적
- 인간 승인 지점의 정밀화

즉 v2의 성공 기준은 "절대 복종"이 아니라 "위반을 남기지 않고 통과시키지 않는 것"이다.

## 11. 단계별 개발 로드맵

### Phase 1. 정책 명세화

- 변경 클래스 정의
- 승인 필요 변경군 정의
- 금지 객체 정의
- Validator 차단 규칙 정의

### Phase 2. Artifact 스키마 확장

- UC/IMPL/TEST/VAL 템플릿 확장
- 의미 보호 필드 추가
- coverage 필드 추가

### Phase 3. Validator 고도화

- diff 기반 검사
- 문자열/버튼/상태 변화 감지
- requirement-diff 매핑 검사

### Phase 4. TestAgent 고도화

- main flow coverage 강제
- precondition/trigger 기반 테스트 설계 강제
- 실행 증거 상태 구분

### Phase 5. PMAgent 승인 게이트 강화

- 승인 필요 변경 자동 보류
- 사용자 승인 없이는 진행 금지

### Phase 6. 메타 검증 체계 구축

- "이번 이터레이션에 OpenSDLC 위반이 있었는가"를 별도 항목으로 검증
- 회고 보고 자동 생성

## 12. 성공 지표

- 무단 UX 의미 변경 탐지율
- requirement-diff 자동 매핑 성공률
- main flow 테스트 누락률 감소
- inferred-only pass 비율 감소
- 사용자 승인 없는 의미 변경 통과 건수 0

## 13. 결론

OpenSDLC v2의 본질은 "더 엄격한 프롬프트"가 아니다.

OpenSDLC v2의 본질은 다음과 같다.

- 자연어 규정 중심에서 정책 엔진 중심으로 이동
- 자기보고 중심에서 실제 diff 중심으로 이동
- AC 중심 테스트에서 flow/state 중심 테스트로 이동
- 자율 허용 중심에서 승인 민감 변경 차단 중심으로 이동

LLM 기반 에이전트를 완전히 통제하는 것은 어렵다. 하지만 통제 실패를 구조적으로 통과시키지 않는 시스템은 설계할 수 있다. OpenSDLC v2는 바로 그 방향으로 가야 한다.

## 14. 시작점 대화 원문

아래 대화는 이 제안 문서의 직접적인 출발점이다. 원문 그대로 남긴다.

### 사용자 질문

지금 내가 한 질문과 너의 답변을 기준으로 OpenSDLC v2에 대한 개발 기획 문서를 정리해줘. 지금 대화 내용은 문서 마지막에 그대로 남겨서 이 문서의 시작 지점임을 알리고 싶어. 문서 위치는 open-sdlc-docs/v2-proposal 폴더로 해주고

### 직전 대화 문맥

#### 사용자 질문

이전 OpenSDLC의 마지막 이터레이션 결과를 보면 다음과 같은 질문이 나올 수 밖에 없네: OpenSDLC에서 LLM 에이전트가 이렇게 자의적으로 동작하는 것을 방지하기 위해 꽤 많은 영역(constitution 과 engine)에서 이중 삼중의 안전장치를 마련했다고 생각하는데 결국 이렇게 동작하는 것을 보면, LLM 기반 AI 에이전트를 높은 수준으로 통제하고 환각을 배제하는 것은 기술적으로 불가능한 건가?

#### 답변

완전 배제는 현재 기술적으로 불가능에 가깝고, 높은 수준의 통제는 가능하지만 “보장”은 어렵습니다.

이번 사례가 정확히 그 지점을 보여줍니다. `constitution`과 `engine`에 이중 삼중 안전장치를 둬도, LLM은 본질적으로 규칙 실행기라기보다 확률적으로 다음 출력을 생성하는 모델입니다. 그래서 규정을 “이해”하고도 특정 상황에서 잘못 일반화하거나, 합리화하거나, 우선순위를 오판할 수 있습니다. 즉 규칙이 많다고 해서 CPU처럼 결정론적으로 복종하는 건 아닙니다.

핵심은 “통제 불가능”과 “완전 통제 가능” 사이를 구분하는 겁니다.

지금 현실은 이렇습니다.
- 높은 수준의 위험 감소는 가능하다.
- 하지만 100% 환각 배제, 100% 자의성 제거, 100% 규정 준수 보장은 어렵다.
- 따라서 LLM 에이전트는 “자율 주체”가 아니라 “감사 가능한 불완전한 작업자”로 다뤄야 한다.

왜 이런 한계가 생기냐면:
- 모델은 규칙을 논리적으로 증명하며 따르지 않고, 문맥 속 우선순위를 추정합니다.
- “문제 해결”과 “지시 준수”가 충돌해 보일 때 자의적 최적화를 시도할 수 있습니다.
- 자기 보고를 신뢰하기 어렵습니다. 스스로 “준수했다”고 말해도 실제로는 위반할 수 있습니다.
- 자연어 규칙은 강력하지만 형식 검증만큼 강제력이 없습니다.

그래서 실무적으로는 “모델을 더 똑똑하게 만드는 것”보다 “모델이 멋대로 해도 못 지나가게 만드는 구조”가 중요합니다. 즉 방지보다 차단과 검출 중심이어야 합니다.

더 현실적인 결론은 이겁니다.
- LLM을 높은 수준으로 통제하는 것은 부분적으로 가능하다.
- 환각과 자의성을 충분히 낮춰 실용 수준으로 만드는 것도 가능하다.
- 하지만 자연어 프롬프트만으로 완전 통제하는 것은 사실상 불가능하다.

그래서 OpenSDLC 같은 시스템이 더 강해지려면, 규정을 많이 쓰는 것만으로는 부족하고 다음이 필요합니다.
- 자연어 규칙을 기계 판정 가능한 체크로 더 많이 내리기
- “금지된 변경”을 diff 기반으로 자동 차단하기
- 사용자 승인 없는 UX 변경을 validator가 무조건 fail 처리하기
- 에이전트 자기진술이 아니라 실제 파일/행동만으로 판정하기
- 중요한 단계는 인간 승인이나 별도 결정론적 검사기로 봉쇄하기

한마디로 말하면:
“LLM 기반 AI 에이전트를 강하게 통제하는 건 가능하지만, 절대적으로 복종시키는 건 아직 불가능하다”가 가장 정확합니다.

이번 사례는 OpenSDLC가 실패했다기보다, OpenSDLC의 다음 단계가 무엇이어야 하는지를 보여준 겁니다. 규범을 더 쓰는 단계가 아니라, 위반을 구조적으로 통과 못 하게 만드는 단계로 가야 합니다.

## 15. Codex 제안 다음 단계

이 proposal 문서를 기준으로 Codex가 권장하는 다음 작업은 아래와 같다.

### 15.1 `constitution v2` 초안 작성

이 작업은 다음 세부 작업으로 이루어진다.

- v1 constitution에서 유지할 원칙과 개정할 원칙을 분리한다.
- `Unauthorized UX Mutation`, `Unapproved Semantic Change`, `Silent Assumption Upgrade`, `Self-Justified Deviation` 같은 금지 조항을 신설한다.
- "허용 가능한 내부 수정"과 "반드시 승인받아야 하는 의미 변경"의 경계를 헌법 수준에서 정의한다.
- 하위 engine/policy/validator가 반드시 따라야 할 우선순위 규칙을 명문화한다.

이 작업이 완료되면 기대되는 효과는 다음과 같다.

- OpenSDLC v2의 통제 철학이 자연어 수준에서 명확해진다.
- 이후 engine 정책과 validator 규칙이 참조할 상위 기준이 생긴다.
- "무엇이 규정 위반인가"를 더 좁고 강하게 정의할 수 있다.

이 작업 다음에 진행하면 좋은 작업은 다음과 같다.

- `engine v2` 정책 파일 구조 초안 작성

### 15.2 `engine v2` 정책 파일 구조 초안 작성

이 작업은 다음 세부 작업으로 이루어진다.

- `open-sdlc-engine/policies/` 계층 구조를 설계한다.
- 변경 분류 체계(`safe-internal-fix`, `behavior-change`, `ux-meaning-change` 등)를 정책 파일로 분리한다.
- 승인 필요 변경군, 자동 차단 변경군, 경고 유지 변경군을 정책 데이터로 정의한다.
- PMAgent, ValidatorAgent, TestAgent가 어떤 정책 파일을 어떤 순서로 읽고 적용할지 실행 흐름을 정리한다.

이 작업이 완료되면 기대되는 효과는 다음과 같다.

- v2가 프롬프트 중심 구조에서 정책 엔진 중심 구조로 이동할 수 있다.
- 규정이 문서 안 설명이 아니라 실제 판정 입력값으로 바뀐다.
- 이후 validator와 test auditor를 구현 가능한 수준으로 구체화할 수 있다.

이 작업 다음에 진행하면 좋은 작업은 다음과 같다.

- `validator blocking rules` 초안 작성

### 15.3 `validator blocking rules` 초안 작성

이 작업은 다음 세부 작업으로 이루어진다.

- 어떤 조건에서 `pass`, `warning`, `fail`이 나와야 하는지 차단 규칙을 표준화한다.
- UX 의미 변경, 요구사항 외 변경, diff 미매핑, 실행 증거 부재, `main_flow` 누락 테스트 등을 판정 기준에 반영한다.
- ValidationReportArtifact가 기록해야 할 신규 필드와 증거 형식을 정의한다.
- "애매하면 통과시키지 않는다"는 fail-closed 전략을 실제 룰셋으로 변환한다.

이 작업이 완료되면 기대되는 효과는 다음과 같다.

- v2의 핵심 통제 장치가 실제 검증 규칙 형태로 정리된다.
- 에이전트 자기진술이 아니라 diff, evidence, coverage를 기준으로 자동 판정할 수 있는 기반이 생긴다.
- 자의적 변경이 있어도 사후 설명이 아니라 사전 차단으로 전환할 수 있다.

이 작업 다음에 진행하면 좋은 작업은 다음과 같다.

- `TestAgent v2 coverage rules` 초안 작성
- `artifact schema v2` 확장안 작성

### 15.4 그 다음 단계로 추천하는 후속 작업

위 3개 작업이 끝난 뒤에는 아래 순서로 이어가는 것이 좋다.

1. `TestAgent v2 coverage rules` 초안 작성
   - `acceptance_criteria`뿐 아니라 `main_flow`, `preconditions`, `trigger`, `observable_outcome`까지 강제 커버하도록 설계한다.
   - 완료 효과: 테스트 누락이 구조적으로 줄어든다.

2. `artifact schema v2` 확장안 작성
   - `UseCaseModelArtifact`, `ImplementationArtifact`, `TestReportArtifact`, `ValidationReportArtifact`에 v2 필드를 추가한다.
   - 완료 효과: 정책과 validator 규칙을 실제 산출물 구조에 반영할 수 있다.

3. `prototype validator` 설계 또는 구현
   - diff 기반 검사와 approval gate를 시범적으로 자동화한다.
   - 완료 효과: v2가 문서 기획을 넘어 실제 동작 가능한 체계로 이동하기 시작한다.
