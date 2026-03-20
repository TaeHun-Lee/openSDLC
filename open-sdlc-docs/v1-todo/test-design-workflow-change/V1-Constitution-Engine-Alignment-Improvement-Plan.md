# OpenSDLC v1 Constitution-Engine Alignment Improvement Plan

## 1. 문서 목적

이 문서는 [분석리포트-20260316-010-constitution-engine-개선후-재교차검증-평가.md](../../anamnesis/분석리포트-20260316-010-constitution-engine-개선후-재교차검증-평가.md)에서 확인된 미해결 및 부분 해결 항목을 실제 작업 계획으로 전환한 실행 문서다.

이번 계획의 1차 목표는 기능 확장이 아니라 다음 문제를 해소하는 것이다.

- 헌법과 엔진이 서로 다른 공식 파이프라인을 설명하는 상태 해소
- 에이전트 역할 정의의 규범-실행 불일치 해소
- `TestDesignArtifact (TD)`의 헌법상 제도화
- Validator 공통 품질 게이트의 구조적 정렬 강화
- `FeedbackArtifact` 문면의 역할 경계 누수 축소
- `Overview.md` 같은 보조 문서 잔여 불일치 정리

## 2. 핵심 원칙

### 2.1 우선순위 원칙

가장 먼저 해결해야 할 것은 엔진 보강이 아니라 헌법-엔진 규범 충돌이다.

그 이유는 다음과 같다.

- `open-sdlc-constitution/01-Foundation-Principles.md`의 우선순위 원칙상 하위 엔진은 상위 규범과 충돌하면 안 된다.
- 따라서 현재 가장 큰 blocker는 `engine`의 세부 완성도보다 `constitution`의 동기화 부족이다.

### 2.2 진행 원칙

- 먼저 헌법 계층을 엔진 현실에 맞춘다.
- 그 다음 엔진의 부분 불일치와 잔여 문면 문제를 정리한다.
- 마지막으로 재교차검증을 다시 수행해 개선 효과를 판정한다.

### 2.3 변경 통제 원칙

- 구조 개정과 문구 정리를 분리한다.
- 한 단계 안에서는 같은 목적의 파일만 묶어서 수정한다.
- 각 단계는 완료 기준을 만족해야 다음 단계로 넘어간다.

## 3. 개선 대상과 우선순위

| 우선순위 | Finding | 상태 | 개선 목표 |
|------|------|------|------|
| P0 | F-01 | 미해결 | 헌법 공식 파이프라인을 엔진과 일치시킴 |
| P0 | F-02 | 미해결 | 헌법의 Code/Test/Coord 역할 정의를 엔진과 일치시킴 |
| P0 | F-03 | 미해결 | `TD-n` ID 및 추적성 규칙을 헌법에 편입 |
| P1 | F-05 | 미해결 | Feedback 문면을 ReqAgent 입력 관점으로 재작성 |
| P1 | F-04 | 부분 해결 | Validator 공통 게이트의 구조적 강제 방식 정리 |
| P2 | F-06 | 부분 해결 | Overview 및 보조 문서 잔여 설명 정리 |

## 4. 권장 작업 순서

전체 작업은 아래 5단계로 진행한다.

1. 헌법 파이프라인 동기화
2. 헌법 역할/아티팩트 제도화
3. 엔진 보조 규칙 정렬
4. 보조 문서 정리
5. 재검증 및 결과 평가

## 5. 단계별 상세 계획

## 5.1 1단계: 헌법 파이프라인 동기화

### 작업 목표

헌법의 공식 파이프라인을 엔진의 현행 구조와 동일하게 맞춘다.

### 대상 Findings

- F-01

### 대상 파일

- `open-sdlc-constitution/02-Architecture-Guidelines.md`
- `open-sdlc-constitution/03-Process-Policies.md`

### 세부 작업

- `No-Shortcut Principle`의 단계 정의를 `TEST-DESIGN` / `TEST-EXECUTION` 분리 구조로 개정
- Process Policies의 단계 설명을 아래 구조로 재정의

```text
UC -> VAL -> TEST-DESIGN -> VAL -> IMPL -> VAL -> TEST-EXECUTION -> VAL -> FB -> VAL
```

- 종료 규칙과 iteration 규칙에서 `TEST-EXECUTION` 검증 완료를 종료 조건에 명시
- PMAgent handoff와 validator gate 위치를 헌법 문면에 반영

### 완료 기준

- 헌법 본문 어디에도 단일 `IMPL -> TEST -> FB` 공식 파이프라인이 남지 않는다.
- 헌법과 엔진 핵심 문서가 같은 파이프라인을 사용한다.

### 기대 효과

- 최상위 규범 충돌이 가장 먼저 해소된다.
- 이후 역할/아티팩트 개정이 일관된 기준 위에서 진행된다.

## 5.2 2단계: 헌법 역할/아티팩트 제도화

### 작업 목표

분리형 테스트 구조와 `TD` 아티팩트를 헌법 제도권에 편입한다.

### 대상 Findings

- F-02
- F-03

### 대상 파일

- `open-sdlc-constitution/04-Agent-Regulations.md`
- `open-sdlc-constitution/05-Artifact-Procedures.md`

### 세부 작업

- `CodeAgent` 입력을 `UC + TD` 기준으로 개정
- `TestAgent`를 `Design Mode` / `Execution Mode` 구조로 재정의
- `CoordAgent`를 `TEST-EXECUTION` 이후 피드백 조정 주체로 명확화
- 아티팩트 ID 규칙에 `TD-n` 추가
- 추적성 규칙에 `IMPL -> UC, TD`, `TEST-EXECUTION -> UC, TD, IMPL` 연결 원칙 반영

### 완료 기준

- 헌법의 역할 정의가 엔진 `agent-definitions.md`, `CodeAgent.txt`, `TestAgent.txt`, `CoordAgent.txt`와 충돌하지 않는다.
- 헌법 ID 규칙에 `TD-n`이 공식 포함된다.

### 기대 효과

- 엔진 개편이 더 이상 헌법 외부의 비공식 구조가 아니게 된다.
- 역할 경계 해석 차이로 인한 운영 혼선이 줄어든다.

## 5.3 3단계: 엔진 보조 규칙 정렬

### 작업 목표

헌법과 엔진이 같은 철학을 사용하도록 validator와 feedback 보조 규칙을 다듬는다.

### 대상 Findings

- F-04
- F-05

### 대상 파일

- `open-sdlc-engine/templates/artifacts/ValidationReportArtifact.yaml`
- `open-sdlc-engine/prompts/agent/ValidatorAgent.txt`
- `open-sdlc-engine/templates/artifacts/FeedbackArtifact.yaml`
- `open-sdlc-engine/prompts/agent/CoordAgent.txt`

### 세부 작업

- Validator 공통 게이트와 단계별 체크의 관계를 명시적으로 정리
- `no-regression`을 어디서 강제할지 템플릿 또는 프롬프트 수준에서 결정
- `FeedbackArtifact.prompt_for_next_iteration`을 ReqAgent가 다음 UC를 재구성할 수 있는 문체로 변경
- CoordAgent 프롬프트에서 "implementation guidance" 표현을 "next-iteration requirement guidance"에 가깝게 조정

### 완료 기준

- Feedback 문면이 직접적인 CodeAgent 실행 명령으로 읽히지 않는다.
- Validator 공통 게이트와 단계별 체크의 매핑이 문서만 읽어도 재현 가능하다.

### 기대 효과

- 역할 경계가 문서 구조뿐 아니라 실제 문면에서도 선명해진다.
- Validator 철학이 헌법과 더 밀착된다.

## 5.4 4단계: 보조 문서 정리

### 작업 목표

핵심 구조와 어긋나는 잔여 설명을 정리한다.

### 대상 Findings

- F-06

### 대상 파일

- `open-sdlc-engine/core-concepts/Overview.md`
- 필요 시 `open-sdlc-engine/core-concepts/artifact-definitions.md`

### 세부 작업

- 아티팩트 종류 및 흐름의 번호 배열을 실제 워크플로우 순서와 맞춤
- 설명 순서와 실행 순서가 엇갈리는 부분 제거
- 관련 예시와 ID 패턴 설명이 최신 구조와 완전히 정렬되는지 점검

### 완료 기준

- Overview를 처음 읽는 독자가 순서 혼선을 겪지 않는다.
- 보조 문서에도 구 파이프라인 잔재가 남지 않는다.

### 기대 효과

- 문서 온보딩 품질이 좋아진다.
- 재검증 시 저신호 잡음이 줄어든다.

## 5.5 5단계: 재검증 및 결과 평가

### 작업 목표

개선 후 실제로 정합성이 회복됐는지 다시 교차검증한다.

### 대상 파일

- `open-sdlc-constitution/*`
- `open-sdlc-engine/core-concepts/*`
- `open-sdlc-engine/prompts/agent/*`
- `open-sdlc-engine/templates/artifacts/*`
- `open-sdlc-docs/anamnesis/` 신규 분석리포트

### 세부 작업

- F-01 ~ F-06 기준으로 해결 여부 재판정
- 새 blocker가 생겼는지 확인
- 해결/부분 해결/미해결 표 작성
- 최종 분석리포트 작성

### 완료 기준

- 최소한 F-01, F-02, F-03은 `해결` 상태가 된다.
- 잔여 이슈가 있더라도 보조 레이어 수준으로 내려간다.

### 기대 효과

- 이번 개선이 문서적 선언이 아니라 실제 정합성 회복으로 입증된다.

## 6. 권장 실행 단위

이번 작업은 아래 3개 작업 묶음으로 실행하는 것이 적절하다.

### 묶음 A: 헌법 동기화

- `02-Architecture-Guidelines.md`
- `03-Process-Policies.md`
- `04-Agent-Regulations.md`
- `05-Artifact-Procedures.md`

### 묶음 B: 엔진 보조 정렬

- `ValidationReportArtifact.yaml`
- `ValidatorAgent.txt`
- `FeedbackArtifact.yaml`
- `CoordAgent.txt`
- `Overview.md`

### 묶음 C: 재검증

- 교차검증
- 결과 리포트 작성

## 7. 완료 판정 기준

이번 개선 계획은 아래 조건을 만족하면 완료로 본다.

1. 헌법과 엔진이 같은 공식 파이프라인을 사용한다.
2. 헌법의 에이전트 역할 정의가 엔진 프롬프트와 충돌하지 않는다.
3. `TD-n`이 헌법상 공식 아티팩트 ID로 인정된다.
4. Feedback 문면이 ReqAgent 입력 관점으로 읽힌다.
5. Validator 공통 게이트와 단계별 체크의 관계가 문서 구조상 설명 가능하다.
6. 재교차검증에서 P0 항목이 모두 해결로 판정된다.

## 8. 리스크와 대응

### 리스크 1. 헌법 개정 중 표현만 바뀌고 실제 의미는 구 구조에 머무를 수 있음

대응:
- 각 조문 수정 후 반드시 엔진 핵심 문서와 1:1 대조한다.

### 리스크 2. Feedback 문면을 너무 약하게 바꿔 다음 이터레이션 지시력이 떨어질 수 있음

대응:
- "구현 지시"가 아니라 "요구 재구성 입력"으로 바꾸되, `done_criteria`와 `priority_tasks`는 유지한다.

### 리스크 3. Validator 규칙을 과도하게 일반화해 단계별 특수성이 희석될 수 있음

대응:
- 공통 게이트와 단계별 게이트를 분리해 병기한다.

## 9. 권장 다음 액션

바로 실행한다면 아래 순서를 권장한다.

1. 묶음 A 수행
2. 중간 교차검토
3. 묶음 B 수행
4. 최종 재검증 리포트 작성

## 10. 한 줄 요약

이번 개선 계획의 핵심은 **엔진을 더 고치는 것보다 먼저 헌법을 현재 엔진 구조에 맞게 비준하고, 그 다음 보조 규칙과 문면 누수를 정리하는 것**이다.
