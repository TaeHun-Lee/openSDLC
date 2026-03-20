# Artifact Properties Definition

artifact_id: string
artifact_type: string
iteration: integer
created_by: string
created_at: string
source_artifact_ids: [string]
status: string
summary: string
instructions_for_next_agent: string

## 항목 상세 설명
*   **artifact_id** : Artifact 고유 ID
*   **artifact_type** : Artifact 종류
*   **iteration** : 현재 반복 차수
*   **created_by** : 생성 Agent 이름
*   **created_at** : 생성 시각
*   **source_artifact_ids** : 이 Artifact 생성에 사용된 이전 Artifact ID 목록
*   **status** : 현재 상태값 (`draft`, `approved`, `implemented`, `feedback-required`, `actionable`, `completed`)
*   **summary** : 사람이 빠르게 읽기 위한 요약
*   **instructions_for_next_agent** : 다음 Agent가 바로 실행할 구체적인 작업 지시

## Validator 관련 확장 속성
아래 속성들은 `ValidationReportArtifact`에서 추가로 사용됩니다.

*   **artifact_id** : ValidationReportArtifact는 `{target_artifact_id}-VAL-{attempt}` 규칙을 따릅니다. 예: `IMPL-01-VAL-02`
*   **validated_artifact_id** : ValidatorAgent가 검증한 대상 Artifact ID
*   **validated_artifact_type** : 검증 대상 Artifact 종류
*   **validated_stage** : 검증이 수행된 워크플로우 단계 (`UC`, `TEST-DESIGN`, `IMPL`, `TEST-EXECUTION`, `FB`)
*   **validation_attempt** : 동일 대상 Artifact에 대한 몇 번째 검증 시도인지 나타내는 순번
*   **validation_result** : 검증 판정 결과 (`pass`, `warning`, `fail`)
*   **checks** : 검증 항목별 결과와 근거 목록
*   **violations** : 실패 또는 중대한 위반 사항 목록
*   **warnings** : 진행은 가능하지만 주의가 필요한 사항 목록
*   **next_action** : 다음 단계 진행 또는 재작업 대상과 이유
*   **blocking_reason** : `fail` 또는 보류 판단의 핵심 이유
*   **rework_target_artifact_id** : 재작업이 필요한 대상 Artifact ID
*   **action_rules** : `validation_result`와 `next_action.action`의 허용 조합 규칙
*   **status_rules** : `validation_result`와 `status`의 정렬 규칙
*   **warning_allowed_actions** : `validation_result = warning`일 때 PMAgent가 선택 가능한 `next_action.action` 목록

### ValidationReportArtifact 상태 해석
*   `approved` : `validation_result = pass` 와 정렬되며 다음 단계 진행 가능
*   `actionable` : `validation_result = warning` 와 정렬되며 PMAgent가 `proceed` 또는 `hold`를 결정
*   `feedback-required` : `validation_result = fail` 와 정렬되며 원 생성 에이전트 재작업 필요

## Feedback 완료/반복 관련 확장 속성
아래 속성들은 `FeedbackArtifact`의 반복 또는 종료 판단을 명확히 하기 위해 사용됩니다.

*   **completion_guidance** : 완료 권고 여부, 근거, 사용자 승인 필요 여부
*   **decision_rules** : 점수, validator 결과, 상태값 사이의 조합 규칙
*   **feedback_delivery** : `CoordAgent -> PMAgent -> ReqAgent` 전달 경로와 사용 규칙
*   **prompt_for_next_iteration** : 다음 이터레이션 Use Case에 반영할 구현 지침
