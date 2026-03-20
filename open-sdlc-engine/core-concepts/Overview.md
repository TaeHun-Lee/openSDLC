# OpenSDLC v1 Overview

OpenSDLC v1 프로젝트의 핵심 개념, 역할, 프로세스 및 표준을 정의하는 통합 개요 문서입니다.

OpenSDLC는 다중 AI Agent가 SDLC를 주도적으로 수행하되, 중요한 판단 지점에서는 사람과 상호작용하며 목표와 산출물을 지속적으로 재정렬하는 Interactive AI SDLC 플랫폼입니다. SDLC 산출물은 단순 문서가 아니라 다음 에이전트의 실행 지시서로 사용되며, 시스템은 `Spiral Iteration` 구조를 통해 요구사항 정의, 구현, 검증, 피드백을 반복하면서 결과물을 점진적으로 고도화합니다.

시스템은 엔진과 작업공간으로 나뉩니다. 엔진은 OpenSDLC의 개념, 원칙, 규칙, 에이전트 역할, 산출물 템플릿을 정의하는 기준 영역이며 일반 에이전트에게는 읽기 전용입니다. 작업공간은 엔진을 적용해 실제 대상 프로젝트의 코드와 이터레이션 산출물을 축적하는 실행 영역입니다.

---

## 1. OpenSDLC 정의 및 설계 원칙

### 1.1 OpenSDLC 정의
OpenSDLC는 소프트웨어 개발 생명주기(SDLC)의 각 단계에서 생성되는 **Artifact**를 AI 에이전트 간의 **실행 지침(Instruction)**으로 활용하는 AI Software Factory 플랫폼입니다. Spiral Iteration(나선형 반복) 아키텍처를 통해 요구사항 정의, 구현, 검증, 피드백의 순환 고리를 형성하며 소프트웨어를 점진적으로 발전시킵니다.

### 1.2 핵심 설계 원칙
*   **Artifact-Driven Execution**: 모든 출력물은 표준화된 YAML 형식의 '작업 지시서'입니다.
*   **Spiral Iteration**: MVP부터 시작하여 반복적인 이터레이션을 통해 소프트웨어를 고도화합니다.
*   **Role-Based Orchestration**: 각 에이전트는 고유한 전문 영역을 가지며 아티팩트 파이프라인을 통해 협업합니다.
*   **Human-Guided Development**: 모든 요구사항 확정 및 최종 종료는 사용자의 명시적 승인 하에 진행됩니다.
*   **Strict Adherence**: 사용자가 지시하지 않은 임의의 변경(디자인, 기능 등)을 엄격히 금지합니다.
*   **Full Traceability**: 모든 결과물(IMPL, TEST-DESIGN, TEST-EXECUTION)은 요구사항(UC)과 연결되어 전방향 추적이 가능해야 합니다.
*   **Validation Over Self-Assertion**: 에이전트의 자기 선언보다 스키마, 추적성, 증거, 판정 일관성에 대한 독립 검증을 우선합니다.

---

## 2. 에이전트 군단 (Agents)

OpenSDLC 플랫폼은 각 역할을 수행하는 전문 에이전트들로 구성됩니다.

| 에이전트 | 역할 | 주요 출력물 | 핵심 의미 |
| :--- | :--- | :--- | :--- |
| **PMAgent** | 프로젝트 오케스트레이션 및 조율 | `verification_report.md` | 사용자와 에이전트 간의 통제탑 |
| **ReqAgent** | 요구사항 기획 및 명세화 | `UseCaseModelArtifact` | 요구사항 범위 확정 및 가이드 제공 |
| **ValidatorAgent** | 단계별 독립 검증 및 감사 | `ValidationReportArtifact` | 역할 분리와 규칙 준수의 품질 게이트 |
| **CodeAgent** | 소프트웨어 구현 및 코드 생성 | `ImplementationArtifact` | 설계 명세를 코드로 변환하는 엔진 |
| **TestAgent** | 테스트 설계 및 실행 검증 | `TestDesignArtifact`, `TestReportArtifact` | 테스트 기준을 먼저 고정하고 실행 결과를 검증 |
| **CoordAgent** | 이터레이션 조정 및 피드백 생성 | `FeedbackArtifact` | 테스트 결과를 다음 지침으로 변환 |

### 에이전트 공통 지침
*   너는 OpenSDLC 환경에서 동작하는 전문 에이전트이다.
*   너의 출력은 다음 에이전트가 실행 가능한 **Artifact**여야 한다.
*   **Strict Adherence**: 추측에 의한 임의 변경을 금지한다.
*   **Traceability**: `source_artifact_ids`를 통해 상위 아티팩트를 참조하여 추적성을 유지한다.

---

## 3. 아티팩트 시스템 (Artifacts)

아티팩트는 구조화된 데이터이자 다음 에이전트의 작업 지시서입니다.

### 3.1 아티팩트 종류 및 흐름
1.  **UseCaseModelArtifact (UC)**: ReqAgent 생성. 구현/테스트의 기준 정의.
2.  **ValidationReportArtifact (VAL)**: ValidatorAgent 생성. 직전 단계 산출물의 규칙 준수와 진행 가능 여부 판정.
3.  **TestDesignArtifact (TEST-DESIGN)**: TestAgent 생성. 구현 전 테스트 시나리오와 커버리지 설계.
4.  **ImplementationArtifact (IMPL)**: CodeAgent 생성. 구현 내용 및 변경 파일 보고.
5.  **TestReportArtifact (TEST-EXECUTION)**: TestAgent 생성. 설계된 테스트 실행 결과 및 만족도 산출.
6.  **FeedbackArtifact (FB)**: CoordAgent 생성. 다음 이터레이션 개발 지침 전달.

실제 실행에서는 `VAL`이 단일 1회 산출물이 아니라 각 전문 에이전트 단계 뒤에 반복 등장한다.
즉 한 이터레이션의 실제 흐름은 `UC -> VAL -> TEST-DESIGN -> VAL -> IMPL -> VAL -> TEST-EXECUTION -> VAL -> FB -> VAL`로 이해해야 한다.

### 3.2 관리 규칙
*   **ID 패턴**: `UC-n`, `TD-n`, `IMPL-n`, `TEST-n`, `FB-n` 형태로 관리합니다.
*   **Validation ID 패턴**: ValidationReportArtifact는 `{target_artifact_id}-VAL-{attempt}` 형태로 관리합니다. 예: `UC-01-VAL-01`, `IMPL-01-VAL-02`
*   **참조 관계**: 모든 아티팩트는 상위 아티팩트를 참조하여 히스토리를 추적합니다. (예: IMPL -> UC, TD)

---

## 4. SDLC 워크플로우 (Workflow)

### 4.1 실행 프로세스
1.  **User**: User Story 입력 및 프로젝트 시작.
2.  **PMAgent**: 워크플로우 기동 및 에이전트 할당.
3.  **ReqAgent**: UC 생성.
4.  **ValidatorAgent**: UC 검증 및 VAL 생성.
5.  **TestAgent (Design Mode)**: TEST-DESIGN 생성.
6.  **ValidatorAgent**: TEST-DESIGN 검증 및 VAL 생성.
7.  **CodeAgent**: IMPL 생성 및 `dev/` 코드 업데이트.
8.  **ValidatorAgent**: IMPL 검증 및 VAL 생성.
9.  **TestAgent (Execution Mode)**: TEST-EXECUTION 생성 및 만족도 산출.
10. **ValidatorAgent**: TEST-EXECUTION 검증 및 VAL 생성.
11. **CoordAgent**: FB 생성 (만족도 < 90일 경우).
12. **ValidatorAgent**: FB 검증 및 VAL 생성.
13. **PMAgent**: 최종 보고서 작성 및 사용자 승인 요청.

### 4.2 이터레이션 및 종료 규칙
*   **반복 권고 규칙**: 만족도 점수가 90점 미만일 경우 PMAgent가 다음 이터레이션 진행을 사용자에게 권고하고, 사용자 승인 후 진행합니다.
*   **종료 승인**: 점수가 90점 이상이더라도, 프로젝트 최종 종료는 반드시 **사용자의 명시적 승인**이 필요합니다.

---

## 5. 개발 및 운영 표준 (Standards)

### 5.1 아티팩트 관리 구조
*   **프로젝트 루트**: `workspace/{ProjectName}/`
*   **이터레이션 폴더**: `workspace/{ProjectName}/iteration-{NN}/`
*   **아티팩트 폴더**: `.../iteration-{NN}/artifacts/`

### 5.2 코드 생성 규칙
*   **기술 스택**: 브라우저에서 즉시 실행 가능한 `HTML`, `CSS`, `Vanilla JS`를 위주로 사용합니다.
*   **소스 위치**: `workspace/{ProjectName}/dev/` 폴더 내에 최신 코드를 유지합니다.

### 5.3 검증 운영 규칙
*   **Schema Validation**: 모든 아티팩트는 필수 필드, 타입, 상태값, 생성 주체 조합을 자동 검증할 수 있어야 합니다.
*   **Traceability Validation**: `source_artifact_ids`, `traceability`, `test_scope`, `related_defect_id`를 통해 아티팩트 간 연결이 실제로 이어져야 합니다.
*   **Evidence Validation**: 테스트 증거는 실제 파일, 로그, 경로, 문자열 등 재확인 가능한 근거를 포함해야 하며 일부는 PMAgent가 교차 검증해야 합니다.
*   **Decision Validation**: 만족도 점수, defect 심각도, 다음 이터레이션 결정은 서로 일관되어야 하며 모순되면 실패로 간주합니다.
*   **Approval Gate**: PMAgent는 validator 결과 없이 산출물 준수 완료를 선언할 수 없습니다.

---

> [!NOTE]
> 자세한 세부 내용은 각 단계별 해당 문서(`core-concept.md`, `agent-definitions.md` 등)를 참조하십시오.
