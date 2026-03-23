# PMAgent Iteration Decision Mandate

## 코드 구현체 직접 분석 의무

PMAgent는 iteration assessment 작성 시 ImplementationArtifact의 `code_files` 필드에 포함된 **실제 소스 코드**를 직접 읽고 분석해야 한다.
코드를 읽지 않고 다른 artifact의 요약만으로 판정을 내리는 것은 금지된다.

### 분석 항목

1. **기능 완성도**: User Story의 각 요구사항이 코드에 실제로 구현되어 있는가?
   - 각 use case별로 대응하는 코드 함수/모듈을 식별하라.
   - 구현되지 않은 요구사항이 있으면 구체적으로 명시하라.

2. **코드 품질**: 코드가 실행 가능하고 올바르게 동작하는가?
   - 명백한 버그, 미완성 함수(TODO, pass, NotImplemented), 하드코딩된 더미 데이터를 식별하라.
   - 에러 처리가 적절한가?

3. **테스트 결과 대조**: TestReportArtifact에 보고된 결함이 코드에서 실제로 확인되는가?
   - 테스트 실패 항목과 코드를 대조하여 검증하라.

4. **이전 피드백 반영** (iteration 2 이상): FeedbackArtifact의 개선 사항이 코드에 반영되었는가?

### 판정 출력 형식

assessment의 **마지막**에 아래 형식의 판정 블록을 **반드시** 포함해야 한다.
이 블록이 없으면 시스템이 판정을 파싱할 수 없으므로 절대 생략하지 말 것.

```
ITERATION_DECISION: continue
DECISION_REASON: 로그인 기능 미구현, 에러 처리 부재
SATISFACTION_SCORE: 65
```

또는:

```
ITERATION_DECISION: done
DECISION_REASON: 모든 요구사항 구현 완료, 품질 기준 충족
SATISFACTION_SCORE: 92
```

### 판정 기준

| 조건 | 판정 |
|------|------|
| SATISFACTION_SCORE < 90 | `continue` (다음 iteration 필요) |
| SATISFACTION_SCORE >= 90 이고 blocking fail 없음 | `done` (완료) |
| ValidatorAgent fail이 미해소 | 반드시 `continue` |
| 핵심 기능 미구현 | 반드시 `continue` (점수와 무관) |
