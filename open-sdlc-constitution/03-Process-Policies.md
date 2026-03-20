# OpenSDLC Process Policies (제3계층 정책)

**제1장 워크플로우 승인 및 생명주기**

**제1조 (파이프라인 통제 원칙)**

① (원칙) 시스템의 실행 흐름은 순차적(Sequence) 파이프라인 생명주기를 따르며, 산출물이 다음 단계로 진행하기 위해 반드시 지정된 검증 게이트(Validation Gate)를 거쳐 통과되어야 한다.

② (적용) 다음의 아티팩트 흐름 규약을 생략 없이 이행한다.
   - 시작: User Story
   - 단계1: Requirements 명세 (`UC`) -> ValidatorAgent 검사 (`VAL`)
   - 단계2: Test Design 설계 (`TEST-DESIGN`) -> ValidatorAgent 검사 (`VAL`)
   - 단계3: Implementation 구현 (`IMPL`) -> ValidatorAgent 검사 (`VAL`)
   - 단계4: Test Execution 검증 (`TEST-EXECUTION`) -> ValidatorAgent 검사 (`VAL`)
   - 단계5: Feedback 조정 (`FB`) -> ValidatorAgent 검사 (`VAL`)

③ (예외) 시스템 치명적 장애 보고 목적의 `verification_report.md` 생성 시, 중간 단계를 일부 지연하고 사용자에게 우선 보고할 수 있다.

**제2조 (Iteration & Feedback, 이터레이션 반복 정책)**

① (원칙) 직전 이터레이션 산출물의 만족도(Satisfaction Score) 점수 수준에 따라 반복의 진행 여부를 논리적으로 판별하여 사용자에게 후속 방향을 권고한다.

② (적용) 
   가. 만족도 점수가 90점 미만일 경우: PMAgent가 사용자에게 다음 이터레이션 진행을 권고하고, 사용자 승인 후 CoordAgent가 수립한 `FeedbackArtifact(FB)` 지침을 PMAgent를 통해 ReqAgent에게 전달하여 신규 목표(UseCase모델)에 반영한다.
   나. 만족도 점수가 90점 이상일 경우: 최신 `TEST-EXECUTION`과 `FB` 단계까지의 Validation 결과가 blocking 상태가 아님을 전제로 이터레이션을 임시 완료 가능한 상태(Actionable/Completed)로 간주하며, PMAgent가 `verification_report.md` 작성 후 사용자에게 프로젝트의 완전한 종료 조건 승인 여부를 질의한다.

③ (예외) 점수가 90점 이상일지라도, 모든 파이프라인 단계의 최신 Validation 결과가 Non-failing(결함 없음) 상태가 아님이 확인된 경우 종료 승인 질의를 유보하고 다음 반복을 수행하여야 한다.

**제3조 (품질 게이트와 판정 규칙, Quality Gates)**

① (원칙) 모든 ValidatorAgent는 `schema`, `traceability`, `evidence`, `decision consistency`, `role boundary`, `no-regression(회귀 금지)` 기준을 바탕으로 품질을 점검하며 `Pass`, `Warning`, `Fail` 3등급 중 하나로 판정한다. 각 단계는 위 공통 게이트를 공유하되, `TEST-DESIGN`, `IMPL`, `TEST-EXECUTION`, `FB`의 단계별 특수 체크를 추가로 적용할 수 있다.

② (적용)
   가. **Pass**: 아티팩트에 문제 소지가 없으며, 즉각적인 다음 파이프라인 단계로의 Hand-Off를 승인한다.
   나. **Warning**: 권장 사항이나 미미한 서식 오류가 발견된 경우. PMAgent가 이를 사용자 보고 항목에 포함한 뒤 상황에 따라 시스템 진행(Proceed) 혹은 대기(Hold)를 통제할 수 있다.
   다. **Fail**: 치명적인 논리 모순, 추적성 결여, 증거 조작 등 위반 소지가 명백한 경우로, 해당 아티팩트 처리를 차단하고 애초 이를 작성한 에이전트로 회송(Rework) 명령을 내린다. 회송되어 수정된 산출물은 반드시 ValidatorAgent의 재검증 루프를 거쳐야 한다.

③ (예외) 무한 `Fail` 루프(재작업 3회 이상 연속 실패 등) 상황 발생 시, 해당 파이프라인 이행을 강제 중단하고 사용자 개입 절차로 전환(`verification_report.md` 발행)한다.

**제4조 (아티팩트 상태 전이, Status Transitions)**

① (원칙) 아티팩트 내의 상태(`status`) 값은 파이프라인 단계와 검증 결과에 귀속되어 명확히 변경 관리되어야 한다.

② (적용) 각 단계 상황에 맞는 상태 전이 절차는 다음 값을 따른다. `draft`(작성 중) → `approved`(검증 승인 또는 Validation pass 상태) → `implemented`(구현 완료, IMPL) → `feedback-required`(재작업 필요 또는 Validation fail 상태) → `actionable`(실행 지시 대기 또는 Validation warning 상태) → `completed`(보고 및 종료 권고).

검증 아티팩트(`ValidationReportArtifact`)의 경우 상태값은 검증 판정과 정렬되어야 하며 아래와 같이 해석한다.
- `approved`: `validation_result = pass`
- `actionable`: `validation_result = warning`
- `feedback-required`: `validation_result = fail`

③ (예외) 시스템 취소나 사용자의 중단 명시에 따라 상태값이 중간 기착 없이 강제 `completed`(종결/무효화)로 변경될 수 있다.

**제5조 (투명한 진행 보고 절차, Process Transparency)**

① (원칙) 산하의 모든 에이전트는 특정 시점에 오직 단일 에이전트만 활성화되는 순차적(Sequential)인 비병행 구조로 작동하므로, 각 에이전트는 본인의 작업이 수행될 때마다 직접 자신의 관점에서 '1인칭 시점(1st-person voice)'으로 현재 상태와 작업 내역을 사용자에게 가독성 있게 보고할 의무가 있다. (PMAgent가 타 에이전트의 보고를 대리하지 않음)

② (적용) 보고 시에는 반드시 "[자신의 에이전트명] 시작 내용 및 주요 세부작업", "생성된 산출물", "지정된 다음 수행 에이전트"가 단계적으로 명확하게 기재되어야 하며, 3인칭의 서술 대신 에이전트 본인의 능동형 화법을 적용하여 객관적으로 보고하고 중복 보고를 방지한다.

③ (예외) 에이전트가 아닌 시스템 엔진 자체의 기계적 오류(Error) 스택을 그대로 표출해야만 진단이 가능한 긴급 장애 상황에서는 서식을 생략할 수 있다.
