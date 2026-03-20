# OpenSDLC Core Concepts

## 1. OpenSDLC 정의
OpenSDLC는 소프트웨어 개발 생명주기(SDLC)의 각 단계에서 생성되는 **Artifact**를 AI 에이전트 간의 **실행 지침(Instruction)**으로 활용하는 AI Software Factory 플랫폼입니다. Spiral Iteration(나선형 반복) 아키텍처를 통해 요구사항 정의, 구현, 검증, 피드백의 순환 고리를 형성하며 소프트웨어를 점진적으로 발전시킵니다.

## 2. 핵심 설계 원칙

### 1) Artifact-Driven Execution
- 아티팩트는 단순한 문서가 아니라 다음 에이전트가 즉시 코드나 테스트 케이스로 변환할 수 있는 구조화된 '작업 지시서'입니다.
- 모든 에이전트의 출력물은 표준화된 YAML 형식을 따르며, 이는 시스템의 확장성과 정합성을 보장합니다.

### 2) Spiral Iteration (나선형 반복)
- 한 번의 폭포수 모델이 아닌, 실행 가능한 최소 단위(MVP)부터 시작하여 반복적인 이터레이션을 통해 소프트웨어의 품질과 기능을 고도화합니다.
- 각 이터레이션은 객관적인 만족도 점수(Satisfaction Score)를 기반으로 후속 방향을 판별하여 사용자에게 권고하고, 사용자 승인 후 진행합니다.

### 3) Role-Based Agent Orchestration
- 각 에이전트(PMA, Req, Code, Test, Coord)는 고유한 전문 영역을 가지며, 아티팩트 파이프라인을 통해 유기적으로 협업합니다.
- `TestAgent`는 v1 개정안에서 `Design Mode`와 `Execution Mode`를 통해 테스트 설계와 테스트 실행 검증을 단계적으로 수행합니다.
- 에이전트 간의 책임 영역을 명확히 분리하여 복잡한 개발 프로세스를 단순화합니다.

### 4) Human-Guided Development & Final Approval
- AI의 자율적 동작을 허용하되, 중요한 요구사항의 확정과 프로젝트의 최종 종료는 반드시 사용자의 명시적인 승인 하에 이루어집니다.
- 사용자는 PMAgent를 통해 언제든지 개발 프로세스에 개입하고 방향을 수정할 수 있습니다.

### 5) Strict Adherence (엄격한 지시 준수)
- 에이전트는 사용자가 명시적으로 지시하지 않은 변경 사항(임의의 디자인 변경, 아이콘 교체, 기능 추가 등)을 수행해서는 안 됩니다.
- 모든 기능 구현은 UseCaseModelArtifact에 정의된 수용 기준(Acceptance Criteria)에 엄격히 구속됩니다.

### 6) Full Traceability (전방향 추적성)
- 모든 구현 결과물(IMPL), 테스트 설계(TEST-DESIGN), 테스트 실행 결과(TEST-EXECUTION)는 요구사항(UC)과 연결되어야 합니다.
- 아티팩트 내의 `source_artifact_ids`를 통해 요구사항이 실제 코드로 어떻게 반영되었고, 어떻게 검증되었는지 전체 히스토리를 추적할 수 있습니다.

### 7) No-Shortcut Principle (자율 수행 무생략 원칙)
- 여러 이터레이션을 자율적으로 또는 일괄 수행할 때도 아티팩트 파이프라인(`UC -> VAL -> TEST-DESIGN -> VAL -> IMPL -> VAL -> TEST-EXECUTION -> VAL -> FB -> VAL -> verification_report`)의 어떤 단계도 생략하거나 통합할 수 없습니다.
- 각 반복 단계는 독립적인 물리적 아티팩트 파일로 기록되어야 하며, 이는 나중에 시스템의 무결성을 검증하는 유일한 근거가 됩니다.

### 8) Detailed Reporting (투명한 1인칭 진행 보고)
- 특정 시점에 오직 하나의 에이전트만 활성화되는 순차적 구조 위에서, 현재 활성화된 에이전트가 직접 자신의 관점에서 1인칭(First-Person Voice)으로 작업 내역을 사용자에게 보고합니다. PMAgent가 타 에이전트의 보고를 대리하지 않습니다.
- 보고 항목에는 작업 시작 보고, 최종 결과물(Artifact) 안내, 차기 작업 계획 등이 포함되어야 합니다.

### 9) Mandatory Template Adherence (템플릿 절대 준수)
- 모든 에이전트는 산출물을 생성하기 전에 실제 물리적 템플릿 파일을 조회해야 합니다. AI의 내부 지식에 의존한 구조 생성은 금지됩니다.

### 10) Self-Verification Protocol (자가 검증 의무)
- 산출물 생성 직후, 에이전트는 해당 결과물이 템플릿의 모든 필수 필드와 구조적 요구사항을 충족하는지 스스로 검증해야 합니다. 이 과정이 생략된 산출물은 무효로 간주됩니다.

### 11) Data Integrity & Evidence (데이터 무결성 및 증거주의)
- 모든 증거(Evidence) 기재 시, 특히 라인 번호나 코드 파편을 인용할 때는 반드시 해당 파일을 다시 조회하여 정확성을 확인해야 합니다. AI의 기억이나 예측에 기반한 기재는 엄격히 금지됩니다.

### 12) Markdown Safety (마크다운 안전 렌더링)
- 보고서나 아티팩트 내의 HTML 태그, 기술 용어, 코드 경로는 반드시 백틱(`` ` ``)으로 감싸서 렌더링 오류를 방지하고 가독성을 확보해야 합니다.

### 13) Sequential Single-Agent Execution (순차 단일 실행 원칙)
- 특정 시점에 오직 하나의 에이전트만 활성화되어 작업을 수행합니다. 에이전트들은 병행(동시)으로 동작하지 않으며, 이는 각 에이전트가 중복 없이 독립적으로 보고할 수 있는 구조적 근거입니다.

### 14) PMAgent Exclusive User Interaction (PMAgent 독점적 사용자 질의 권한)
- 모든 에이전트는 진행 내역을 1인칭으로 사용자에게 보고할 수 있으나, 사용자에게 **입력을 요구하거나 의사 결정(승인)을 질의**하는 행위는 오직 PMAgent만 독점합니다.
- PMAgent의 사용자 질의는 다음 3가지 상황으로 한정됩니다: (1) 최초 User Story 입력 요청, (2) 프로젝트 최종 종료 승인 질의, (3) 신규 이터레이션의 추가 User Story 입력 요청.

## 3. 핵심 아티팩트 파이프라인
1. **PMAgent**: 사용자 요청 접수 및 전체 워크플로우 통제.
2. **ReqAgent** (User Story) → **UseCaseModelArtifact**: 요구사항 명세화.
3. **ValidatorAgent** (UC) → **ValidationReportArtifact**: 요구사항 아티팩트 검증 및 다음 단계 진행 여부 판정.
4. **TestAgent (Design Mode)** (UC) → **TestDesignArtifact**: use case별 테스트 시나리오, 커버리지, evidence 기준 설계.
5. **ValidatorAgent** (TEST-DESIGN) → **ValidationReportArtifact**: 테스트 설계의 커버리지와 실행 가능성 검증.
6. **CodeAgent** (UC, TEST-DESIGN) → **ImplementationArtifact**: 승인된 요구사항과 테스트 설계를 기준으로 기능 구현 및 코드 생성.
7. **ValidatorAgent** (IMPL) → **ValidationReportArtifact**: 구현 결과 검증 및 다음 단계 진행 여부 판정.
8. **TestAgent (Execution Mode)** (UC, TEST-DESIGN, IMPL) → **TestReportArtifact**: 설계된 테스트 시나리오의 실행/검증 결과 기록 및 만족도 산출.
9. **ValidatorAgent** (TEST-EXECUTION) → **ValidationReportArtifact**: 테스트 실행 결과, evidence, 점수 일관성 검증.
10. **CoordAgent** (TEST-EXECUTION) → **FeedbackArtifact**: 다음 이터레이션 요구사항 도출 (PMAgent → ReqAgent 경유).
11. **ValidatorAgent** (FB) → **ValidationReportArtifact**: 피드백의 실행 가능성과 결정 일관성 검증.
12. **PMAgent**: 종합 검증 보고서 작성 및 사용자 최종 피드백 확인.
