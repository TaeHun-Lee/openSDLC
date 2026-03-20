# OpenSDLC v1 Validation Execution Preparation

## 1. 문서 목적

이 문서는 `constitution`-`engine` 정렬 개정 이후, 실제 검증 실행을 시작하기 전에 필요한 준비 상태를 정리한 문서다.

목표는 다음 3가지다.

- 지금 바로 검증을 시작할 수 있는지 판단
- 어떤 프로젝트/이터레이션을 검증 대상으로 잡을지 결정
- 검증 시작 전에 필요한 준비물과 체크포인트를 명확히 정리

## 2. 현재 준비 상태 요약

### 2.1 규범 및 엔진 정렬 상태

현재 문서 기준으로는 검증을 시작할 수 있는 상태다.

- 헌법과 엔진은 동일한 공식 파이프라인을 사용한다.
- `TEST-DESIGN`과 `TEST-EXECUTION` 분리 구조가 상위 규범부터 하위 템플릿까지 정렬되어 있다.
- `ValidationReportArtifact`와 `FeedbackArtifact`도 최신 구조에 맞게 정리되어 있다.

즉, **규칙 세트 자체는 검증 가능 상태**다.

### 2.2 기존 워크스페이스 상태

기존 워크스페이스는 참고용으로는 유효하지만, 새 구조의 완전 검증 대상으로는 적합하지 않다.

확인 결과:

- `workspace/TetrisLikeGame/iteration-02/artifacts`
- `workspace/PostItWebApp/iteration-09/artifacts`

둘 다 아래 파일 세트는 존재한다.

- `UC-*`
- `UC-*-VAL-*`
- `IMPL-*`
- `IMPL-*-VAL-*`
- `TEST-*`
- `TEST-*-VAL-*`
- `FB-*`
- `FB-*-VAL-*`

하지만 둘 다 아래 파일이 없다.

- `TD-*`
- `TD-*-VAL-*`

따라서 현재 남아 있는 기존 이터레이션들은 **구 파이프라인 산출물**이며, 새 구조의 핵심인 `TEST-DESIGN` 단계를 통과한 실제 샘플이 아니다.

## 3. 준비 판정

### 최종 판정

**검증 진행 준비는 완료 가능 상태이나, 실제 리허설은 기존 이터레이션 재사용이 아니라 신규 이터레이션 기동 방식으로 진행하는 것이 적절하다.**

### 이유

기존 산출물은 아래 항목을 충족하지 못한다.

- `TEST-DESIGN` 생성 여부
- `TEST-DESIGN` validation gate 통과 여부
- `IMPL -> TEST-EXECUTION`가 `TD`를 참조하는 최신 추적성 체인

즉, 지금 필요한 것은 "기존 결과물 검토"가 아니라 **최신 규칙 세트로 한 번 새로 돌려보는 검증 리허설**이다.

## 4. 권장 검증 방식

## 4.1 권장안

새 프로젝트 또는 새 이터레이션 1건을 처음부터 최신 파이프라인으로 실행한다.

권장 흐름:

```text
User Story 확정
-> workspace/bootstrap
-> UC
-> UC-VAL
-> TD
-> TD-VAL
-> IMPL
-> IMPL-VAL
-> TEST
-> TEST-VAL
-> FB
-> FB-VAL
-> verification_report
```

## 4.2 비권장안

기존 `PostItWebApp` 또는 `TetrisLikeGame` 이터레이션을 그대로 "최종 검증" 대상으로 쓰는 방식은 비권장이다.

이유:

- `TD`가 없어서 최신 파이프라인 완전성을 검증할 수 없다.
- validator의 `common_required_checks` + 단계별 체크가 새 구조에 맞게 작동하는지 확인하기 어렵다.
- feedback 문면이 ReqAgent 경계 안에서 자연스럽게 동작하는지도 확인할 수 없다.

## 5. 권장 검증 대상

### 옵션 A. 신규 검증 전용 프로젝트

예시:

- `workspace/ValidationPilot/`

장점:

- 과거 산출물 영향이 없다.
- 순수하게 최신 구조만 검증할 수 있다.
- 산출물 세트가 깔끔하게 남는다.

단점:

- User Story를 새로 정의해야 한다.

### 옵션 B. 기존 프로젝트의 신규 이터레이션

예시:

- `workspace/PostItWebApp/iteration-10/`
- `workspace/TetrisLikeGame/iteration-03/`

장점:

- 기존 코드베이스를 재사용할 수 있다.
- 회귀 검증 관점이 더 강하다.

단점:

- 이전 이터레이션이 구 구조라 문맥 혼합 가능성이 있다.
- 새 구조 검증인지 기존 산출물 보정인지 경계가 흐려질 수 있다.

### 권장 선택

가장 안전한 선택은 **옵션 A: 신규 검증 전용 프로젝트**다.

## 6. 검증 시작 전 체크리스트

아래 항목이 모두 준비되면 바로 검증을 시작할 수 있다.

### 6.1 입력 준비

- 검증용 User Story 1건 확정
- 범위가 작고 end-to-end 검증 가능한 요구로 제한
- 명확한 acceptance criteria 포함

### 6.2 경로 준비

- `workspace/{ProjectName}/`
- `workspace/{ProjectName}/dev/`
- `workspace/{ProjectName}/iteration-01/`
- `workspace/{ProjectName}/iteration-01/artifacts/`

### 6.3 산출물 기대 세트 준비

아래 파일이 모두 생성되는지 확인해야 한다.

- `UC-01.yaml`
- `UC-01-VAL-01.yaml`
- `TD-01.yaml`
- `TD-01-VAL-01.yaml`
- `IMPL-01.yaml`
- `IMPL-01-VAL-01.yaml`
- `TEST-01.yaml`
- `TEST-01-VAL-01.yaml`
- `FB-01.yaml`
- `FB-01-VAL-01.yaml`
- `verification_report.md`

### 6.4 검증 포인트 준비

- `IMPL`이 `UC + TD`를 참조하는가
- `TEST`가 `UC + TD + IMPL`를 참조하는가
- `ValidationReportArtifact`가 `common_required_checks`와 stage checks를 함께 반영하는가
- `FeedbackArtifact`가 ReqAgent 입력 문체를 유지하는가
- `verification_report.md`가 `TEST-DESIGN`과 `TEST-EXECUTION`을 분리 보고하는가

## 7. 권장 실행 순서

1. 검증 전용 User Story 확정
2. 신규 프로젝트 워크스페이스 부트스트랩
3. 최신 규칙 기준으로 iteration 1 전체 수행
4. 생성 산출물 세트 점검
5. verification_report 작성
6. 교차검토 메모 또는 리허설 평가 리포트 작성

## 8. 준비 단계 산출물

이번 준비 단계에서 확보된 판단은 다음과 같다.

- 규칙 세트 정렬 완료
- 기존 샘플은 참고용일 뿐 최신 구조 검증용으로는 부적합
- 신규 검증 전용 프로젝트 방식이 최적

## 9. 다음 액션 제안

바로 다음 단계로는 아래 순서를 권장한다.

1. 검증용 User Story 1건 선택
2. `workspace/ValidationPilot/` 생성
3. iteration 1 리허설 실행

## 10. 한 줄 요약

지금은 **검증을 시작할 준비는 끝났고, 실제 검증은 기존 이터레이션 재사용이 아니라 신규 검증 전용 프로젝트를 최신 파이프라인으로 한 번 처음부터 돌리는 방식**이 가장 적절하다.
