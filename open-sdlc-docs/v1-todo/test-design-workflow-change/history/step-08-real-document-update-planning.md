# Step 08 - Real Document Update Planning

## 단계 대상 작업

- 실제 v1 문서 반영을 위한 수정 파일 묶음 확정
- 수정 순서와 선행/후행 관계 정리
- 반영 시 정합성 위험과 체크포인트 정리

## 작업 진행 계획

- 현재까지 확정한 워크플로우, 아티팩트, 에이전트, Validator 기준 초안을 실제 수정 대상 파일에 매핑한다.
- 어떤 파일을 한 묶음으로 수정해야 정합성이 유지되는지 정리한다.
- 수정 순서를 정하고, 각 묶음의 완료 조건과 검토 포인트를 정의한다.
- 이후 실제 반영 단계에서 바로 사용할 수 있도록 실행 순서를 고정한다.

## 기대 효과

- 실제 운영 문서 반영을 안전하게 시작할 수 있다.
- 파일별 충돌과 누락 가능성을 줄일 수 있다.
- 논리 단위별 커밋 또는 검토 단위를 자연스럽게 나눌 수 있다.

## 예상 변경 범위

- 이번 단계는 반영 계획과 작업 이력 문서 정리에 집중한다.
- 실제 운영 문서 본문은 아직 수정하지 않는다.
- 작업 이력 문서만 신규 생성한다.

## 작업 결과

### 1. 실제 수정 대상 파일 묶음

#### 묶음 A - 워크플로우/개념 문서

- `open-sdlc-engine/core-concepts/workflow.md`
- `open-sdlc-engine/core-concepts/core-concept.md`
- `open-sdlc-engine/core-concepts/agent-definitions.md`

목적:
- 공식 파이프라인을 `UC -> VAL -> TEST-DESIGN -> VAL -> IMPL -> VAL -> TEST-EXECUTION -> VAL -> FB -> VAL`로 변경
- `TestAgent`의 2모드 구조를 공식 정의에 반영
- `CodeAgent`, `ValidatorAgent`, `PMAgent`의 입력/책임 변경을 개념 문서에 맞춤

#### 묶음 B - 아티팩트 템플릿

- `open-sdlc-engine/templates/artifacts/TestReportArtifact.yaml`
- `open-sdlc-engine/templates/artifacts/ValidationReportArtifact.yaml`
- `open-sdlc-engine/templates/artifacts/ImplementationArtifact.yaml`
- 신규 `open-sdlc-engine/templates/artifacts/TestDesignArtifact.yaml`

필요 시 검토:
- `open-sdlc-engine/core-concepts/artifact-definitions.md`
- `open-sdlc-engine/templates/artifacts/DescriptionOfArtifactProperties.md`

목적:
- `TestDesignArtifact` 신규 도입
- `TestReportArtifact`를 `TEST-EXECUTION` 전용 결과 아티팩트로 재정의
- `ValidationReportArtifact`의 `stage_check_guidance` 확장
- `ImplementationArtifact`가 `TestDesignArtifact`를 상위 참조로 다루도록 조정 여부 검토

#### 묶음 C - 에이전트 프롬프트

- `open-sdlc-engine/prompts/agent/TestAgent.txt`
- `open-sdlc-engine/prompts/agent/CodeAgent.txt`
- `open-sdlc-engine/prompts/agent/ValidatorAgent.txt`
- `open-sdlc-engine/prompts/agent/PMAgent.txt`

검토 가능:
- `open-sdlc-engine/prompts/agent/AgentCommon.txt`

목적:
- `TestAgent` Design/Execution 모드 분리
- `CodeAgent` 입력 확장
- `ValidatorAgent`의 `TEST-DESIGN`/`TEST-EXECUTION` 판정 기준 반영
- `PMAgent` handoff 및 completeness 검사 확장

#### 묶음 D - 시스템 부트스트랩/보고서

- `open-sdlc-engine/prompts/system/initial-system-prompt.md`
- `open-sdlc-engine/prompts/system/initial-system-prompt-codex.md`
- `open-sdlc-engine/templates/reports/verification_report.md`

목적:
- 부트스트랩 문서가 새 파이프라인을 읽도록 정렬
- verification report가 `TEST-DESIGN`, `TEST-EXECUTION`을 별도로 요약하도록 수정

#### 묶음 E - 설정/보조 문서

- `open-sdlc-engine/agent-configs/TestAgent.config.yaml`
- `open-sdlc-engine/agent-configs/README.md`

검토 대상:
- 다른 `agent-configs/*.yaml`

목적:
- 필요 시 에이전트 설명/설정 메타데이터를 최신 구조와 맞춤
- 운영 문서만 바뀌고 설정 문서가 뒤처지는 문제 방지

### 2. 권장 수정 순서

#### 1순위 - 묶음 A: 워크플로우/개념 문서

이유:
- 전체 구조와 용어를 먼저 고정해야 이후 템플릿과 프롬프트가 흔들리지 않는다.

완료 기준:
- 공식 파이프라인이 새 구조로 명시된다.
- `TestAgent` 2모드 구조가 문서상 명확하다.

#### 2순위 - 묶음 B: 아티팩트 템플릿

이유:
- 프롬프트는 템플릿을 따라야 하므로 템플릿이 먼저 안정화되어야 한다.

완료 기준:
- `TestDesignArtifact.yaml`이 생긴다.
- `TestReportArtifact.yaml`와 `ValidationReportArtifact.yaml`이 새 단계 구조를 반영한다.

#### 3순위 - 묶음 C: 에이전트 프롬프트

이유:
- 프롬프트가 새 템플릿과 새 워크플로우를 정확히 따르도록 맞춰야 한다.

완료 기준:
- `TestAgent`, `CodeAgent`, `ValidatorAgent`, `PMAgent`가 새 입력/출력/판정 구조를 명시한다.

#### 4순위 - 묶음 D: 시스템 부트스트랩/보고서

이유:
- 최상위 진입 프롬프트와 최종 보고서가 새 구조를 누락하면 운영 모드 전체가 어긋난다.

완료 기준:
- 부트스트랩 문서의 읽기 순서와 파이프라인 설명이 최신화된다.
- `verification_report.md`에 TEST 관련 요약이 둘로 분리된다.

#### 5순위 - 묶음 E: 설정/보조 문서

이유:
- 핵심 운영 규칙 반영 후, 설정과 설명 문서를 뒤따라 정리하는 편이 안전하다.

완료 기준:
- 설정/README류 문서가 최신 구조와 모순되지 않는다.

### 3. 묶음별 위험 요소

#### 묶음 A 위험

- 워크플로우 문서와 에이전트 정의 문서의 용어가 달라질 수 있음
- `TEST` 용어를 일부 문서만 바꾸면 혼동 발생

#### 묶음 B 위험

- `ImplementationArtifact`의 상위 참조 구조를 어떻게 둘지 불명확할 수 있음
- `ValidationReportArtifact`에서 새 stage 명칭을 반영하지 않으면 validator 프롬프트와 충돌 가능

#### 묶음 C 위험

- `TestAgent` 모드 분리가 애매하면 다시 역할 혼합이 발생
- `CodeAgent`가 `TestDesignArtifact`를 읽는다고 적어도 실제 산출물 구조가 안 맞으면 정합성 깨짐

#### 묶음 D 위험

- 시스템 부트스트랩 문서가 옛 순서를 유지하면 운영 모드가 잘못 초기화될 수 있음
- 최종 보고서가 `TEST-DESIGN` 결과를 누락하면 completeness 판단이 왜곡될 수 있음

### 4. 수정 전/후 체크포인트

수정 전 확인:
- 새 공식 용어를 통일한다
  - `TEST-DESIGN`
  - `TEST-EXECUTION`
  - `TestDesignArtifact`

수정 후 확인:
- 워크플로우 문서와 에이전트 정의가 같은 순서를 말하는가
- 템플릿과 프롬프트가 같은 artifact id/type을 말하는가
- `ValidationReportArtifact`의 `stage_check_guidance`가 프롬프트 설명과 일치하는가
- verification report가 새 단계 구조를 모두 반영하는가

### 5. 권장 실제 반영 시작점

가장 자연스러운 다음 작업은 다음 순서다.

1. 묶음 A 실제 수정
2. 묶음 B 실제 수정
3. 사용자 중간 확인
4. 묶음 C 실제 수정
5. 묶음 D/E 실제 수정
6. 최종 검토

이렇게 하면 구조 문서와 템플릿이 먼저 안정화된 뒤 프롬프트가 따라가므로 위험이 줄어든다.

### 6. 현 단계 결론

- 실제 반영은 충분히 진행 가능한 상태다.
- 다만 한 번에 전 파일을 수정하기보다 `묶음 A -> 묶음 B -> 확인 -> 묶음 C -> 묶음 D/E` 순서가 가장 안전하다.

## 사용자 확인 상태

- 8단계 결과를 사용자에게 보고 후 확인 요청 예정
- 승인 시 다음 단계는 묶음 A 실제 수정으로 진행 가능

## 다음 단계

- `Step 09 - Real Update Group A`
- 목표: `workflow.md`, `core-concept.md`, `agent-definitions.md` 실제 수정
