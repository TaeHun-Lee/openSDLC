# Step 12 - Real Update Group D

## 단계 대상 작업

- 시스템 부트스트랩 프롬프트 실제 수정
- `verification_report.md` 템플릿 실제 수정
- 새 워크플로우가 시스템 진입점과 최종 보고서까지 반영되도록 정렬

## 작업 진행 계획

- `initial-system-prompt.md`, `initial-system-prompt-codex.md`에 새 테스트 단계와 템플릿 읽기 순서를 반영한다.
- `verification_report.md` 템플릿에 `TEST-DESIGN`과 `TEST-EXECUTION` 검증 요약을 추가한다.
- 수정 후, 부트스트랩과 최종 보고서가 새 워크플로우를 빠뜨리지 않는지 검토한다.

## 기대 효과

- OpenSDLC를 다시 부팅할 때도 새 파이프라인을 읽게 된다.
- 최종 iteration 보고서가 테스트 설계와 테스트 실행을 분리해 설명할 수 있게 된다.
- 워크플로우/템플릿/프롬프트/부트스트랩/보고서까지 핵심 축이 모두 정렬된다.

## 예상 변경 범위

- `open-sdlc-engine/prompts/system/initial-system-prompt.md`
- `open-sdlc-engine/prompts/system/initial-system-prompt-codex.md`
- `open-sdlc-engine/templates/reports/verification_report.md`

## 작업 결과

### 수정 파일

- `open-sdlc-engine/prompts/system/initial-system-prompt.md`
- `open-sdlc-engine/prompts/system/initial-system-prompt-codex.md`
- `open-sdlc-engine/templates/reports/verification_report.md`

### 반영 내용 요약

#### 1. `initial-system-prompt.md`

- Step 4 template reading order에 `TestDesignArtifact.yaml`을 추가했다.
- 템플릿 참조 목록 순서를 새 구조에 맞게 조정했다.
- 합성 운영 프롬프트 필수 명시 항목에 아래를 추가했다.
  - `TEST-DESIGN`은 구현 전에 위치한다
  - `TEST-EXECUTION`은 구현 후에 위치한다

#### 2. `initial-system-prompt-codex.md`

- Codex용 부트스트랩 프롬프트에도 `TestDesignArtifact.yaml`을 추가했다.
- 필수 명시 항목에 새 테스트 단계 구조를 반영했다.
- 실행 잠금 규칙과 충돌 없이 새 파이프라인을 읽도록 정렬했다.

#### 3. `verification_report.md`

- 검토 범위를 `UC/TEST-DESIGN/IMPL/TEST-EXECUTION/FB` 기준으로 수정했다.
- `Validator Gate Summary`에 아래 항목을 분리 추가했다.
  - `TEST-DESIGN Validation`
  - `TEST-EXECUTION Validation`

### 수정 후 검토 결과

- 부트스트랩 프롬프트 2개 모두 새 템플릿 목록과 새 파이프라인을 읽는다.
- 최종 보고서 템플릿도 더 이상 옛 `TEST` 단일 단계만 전제하지 않는다.
- 현재까지 핵심 운영 파일들은 새 테스트 설계/실행 분리 구조와 모순 없이 정렬됐다.

## 사용자 확인 상태

- 12단계 결과를 사용자에게 보고 후 확인 요청 예정
- 승인 시 다음 단계는 묶음 E 및 보조 문서 정리 또는 최종 검토로 진행

## 다음 단계

- `Step 13 - Supporting Docs And Final Review`
- 목표: 보조 문서/설정 반영 필요 여부 점검 후 전체 정합성 최종 검토
