# SDLC 워크플로우 (Workflow)

OpenSDLC v1의 전체 실행 흐름과 에이전트 간의 상호작용 규칙입니다.

> **순차 단일 실행 원칙**: 특정 시점에 오직 하나의 에이전트만 활성화되어 작업을 수행합니다. 에이전트들은 병행(동시)으로 동작하지 않으며, 각 에이전트는 자신의 작업을 1인칭으로 직접 보고합니다.

## 1. 전체 실행 프로세스
1. **User**: User Story 입력 및 프로젝트 시작 지시
2. **PMAgent**: 워크플로우 기동 및 에이전트 할당
3. **ReqAgent**: `UseCaseModelArtifact` (UC) 생성
4. **ValidatorAgent**: `ValidationReportArtifact` (VAL) 생성 및 UC 검증
5. **TestAgent (Design Mode)**: `TestDesignArtifact` (TEST-DESIGN) 생성
6. **ValidatorAgent**: `ValidationReportArtifact` (VAL) 생성 및 TEST-DESIGN 검증
7. **CodeAgent**: `ImplementationArtifact` (IMPL) 생성 및 `dev/` 코드 업데이트
8. **ValidatorAgent**: `ValidationReportArtifact` (VAL) 생성 및 IMPL 검증
9. **TestAgent (Execution Mode)**: `TestReportArtifact` (TEST-EXECUTION) 생성
10. **ValidatorAgent**: `ValidationReportArtifact` (VAL) 생성 및 TEST-EXECUTION 검증
11. **CoordAgent**: `FeedbackArtifact` (FB) 생성 (다음 이터레이션 가이드)
12. **ValidatorAgent**: `ValidationReportArtifact` (VAL) 생성 및 FB 검증
13. **PMAgent**: `verification_report.md` 작성 및 사용자에게 최종 확인 요청

---

## 2. 이터레이션 및 종료 규칙

### 1) 자동화 규칙 (Orchestration Policy)
- **Validator Fail**: ValidatorAgent가 `fail`을 판정하면 해당 산출물은 다음 단계로 전달되지 않으며, 원래 생성 에이전트가 재작업을 수행합니다.
- **Validator Warning**: ValidatorAgent가 `warning`을 판정하면 PMAgent는 경고를 보고한 뒤 다음 단계 진행 여부를 결정합니다.
- **Validator Pass**: ValidatorAgent가 `pass`를 판정하면 다음 에이전트로 정상 전달할 수 있습니다.
- **TEST-DESIGN Pass**: 승인된 테스트 설계가 준비된 경우에만 CodeAgent가 구현을 시작합니다.
- **TEST-EXECUTION Fail**: 실행 결과의 실패 원인이 구현 결함이면 PMAgent는 CodeAgent 재작업 루프로 되돌릴 수 있습니다.
- **만족도 점수 < 90**: PMAgent가 사용자에게 다음 이터레이션 진행을 권고하고, 사용자 승인 후 CoordAgent의 FeedbackArtifact를 PMAgent를 경유하여 ReqAgent에게 전달합니다. ReqAgent는 피드백 항목을 신규 이터레이션의 Use Case에 반영하여 전체 파이프라인을 다시 수행합니다.
- **만족도 점수 >= 90**: 이터레이션을 종료할 수 있는 품질 수준에 도달한 것으로 판단합니다.

### 2) 종료 승인 (Final Approval)
- **종료 우선순위**: `Validator Fail > 추가 재작업 > completion recommendation > 사용자 승인 요청` 순서로 판단합니다.
- ValidatorAgent의 blocking `fail`이 하나라도 남아 있으면, 만족도 점수가 90 이상이어도 종료할 수 없습니다.
- 만족도가 90점 이상이더라도, 프로젝트의 최종 종료는 반드시 **사용자의 명시적인 승인**이 있을 때만 가능합니다.
- 사용자 승인 전까지는 이터레이션을 반복하거나 추가 요구사항을 반영할 수 있습니다.

---

## 3. 품질 게이트 (Quality Gates)
- **단계별 검증 게이트**: 각 전문 에이전트 산출물은 ValidatorAgent의 검증을 통과해야만 다음 단계로 넘어갈 수 있음.
- **테스트 설계 선행 원칙**: 구현 전에 `TEST-DESIGN` 단계가 먼저 승인되어야 하며, 구현 이후에는 승인된 테스트 설계 기준으로만 실행 검증을 수행함.
- **추적성 준수**: 모든 결과물은 상위 아티팩트를 참조해야 함.
- **회귀 금지**: 기존에 통과된 기능은 다음 이터레이션에서 훼손되지 않아야 함.
- **지시 준수**: 사용자가 지시하지 않은 임의의 레이아웃이나 아이콘 변경은 결함(Defect)으로 간주함.
- **작업공간 준비 책임**: 프로젝트 경로, 이터레이션 폴더, `artifacts/`, 보고서 출력 경로 같은 작업공간 준비는 PMAgent가 선행 책임을 가지며, 다른 에이전트는 준비된 경로를 전제로 자신의 본업만 수행함.

## 4. 아티팩트 상태 값 (Status Values)
- `draft`: 작성 중
- `approved`: 지침으로 활용 가능
- `implemented`: 구현 완료
- `feedback-required`: 추가 보완 필요
- `actionable`: 실행 대기 중
- `completed`: 최종 완료 및 종료 권고

### ValidationReportArtifact 상태 해석
- `approved`: `validation_result: pass` 와 정렬되며 다음 단계 진행이 가능함
- `actionable`: `validation_result: warning` 과 정렬되며 경고를 유지한 채 PMAgent가 진행 또는 보류를 결정함
- `feedback-required`: `validation_result: fail` 과 정렬되며 원 생성 에이전트의 재작업이 필요함
