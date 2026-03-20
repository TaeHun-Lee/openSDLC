# CLAUDE.md — OpenSDLC v1 Implementation Guide

이 파일은 Claude CLI(Claude Code)가 프로젝트 진입 시 자동으로 읽는 컨텍스트 파일이다.
OpenSDLC v1의 방법론 명세를 실행 가능한 코드로 구현하는 작업의 배경, 설계 결정, 구현 전략을 담고 있다.

---

## 1. 프로젝트 배경

OpenSDLC는 소프트웨어 개발 생명주기(SDLC)의 각 단계를 담당하는 AI Agent들이
구조화된 아티팩트(YAML)를 통해 유기적으로 협업하는 AI Software Factory 플랫폼이다.

### 현재 상태
- `open-sdlc-constitution/`, `open-sdlc-engine/`, `open-sdlc-docs/`에 **방법론 명세**가 완성되어 있음
- 6종의 아티팩트 스키마(UC, TEST-DESIGN, IMPL, TEST-EXECUTION, FB, VAL)가 정의됨
- 12단계 파이프라인에 5개 Validation 게이트가 설계됨
- **아직 실행 런타임(코드)이 없음** — 현재는 단일 LLM 대화에서 1인다역으로 테스트 중

### 핵심 문제 (구현 동기)
현재 하나의 LLM이 모든 Agent 역할을 순차적으로 수행하다 보니:
- ValidatorAgent가 자기가 방금 본 ReqAgent의 사고 과정을 기억한 채로 검증 → 항상 pass
- "자기가 쓴 답안을 자기가 채점하는" 구조적 한계
- 이 문제를 **Agent별 독립 context session**으로 해결하는 것이 구현의 핵심 목표

---

## 2. 구현 목표: PoC (Proof of Concept)

### PoC 범위
전체 12단계가 아닌, **최소 3노드 루프**만 먼저 구현한다:

```
ReqAgent → ValidatorAgent → (fail 시) ReqAgent 재작업
                           → (pass 시) CodeAgent
```

### PoC 성공 기준
1. ValidatorAgent가 결함 있는 UC artifact에 대해 **실제로 `fail`을 판정**하는 것
2. fail 판정 후 ReqAgent가 재작업하여 **품질이 향상**되는 것
3. 위 과정에서 각 Agent가 **독립된 LLM API 호출**로 실행되어, 서로의 context를 공유하지 않는 것

### PoC에 포함하지 않는 것
- TestAgent, CoordAgent, PMAgent 구현
- GUI 프론트엔드
- 다중 iteration (Spiral 반복)
- 프로젝트 관리 기능

---

## 3. 기술 스택

| 구성요소 | 기술 | 이유 |
|----------|------|------|
| Agent 오케스트레이션 | **LangGraph** | 상태 머신 기반, 조건부 라우팅(pass/fail), 체크포인트 |
| LLM API | **Anthropic Claude API** | 프로젝트 주력 모델 |
| API 서버 | **FastAPI** (PoC 후반부) | WebSocket 지원, 비동기 |
| 런타임 | **Python 3.11+** | LangGraph/LangChain 호환 |

---

## 4. 아키텍처 핵심: Context 격리

### 원칙
각 Agent는 **별도의 LLM API 호출(messages.create)**로 실행된다.
Agent 간에 전달되는 것은 오직 **YAML 아티팩트 문자열**뿐이다.

### ReqAgent 호출 구조
```
system_prompt: open-sdlc-engine/prompts/agent/req-agent.md 내용
               + open-sdlc-constitution/ 핵심 원칙 발췌
               + open-sdlc-engine/templates/UseCaseModelArtifact 템플릿
user_message:  사용자의 User Story (최초)
               또는 ValidatorAgent의 fail 사유 + 이전 UC artifact (재작업 시)
output:        UseCaseModelArtifact (YAML)
```

### ValidatorAgent 호출 구조
```
system_prompt: open-sdlc-engine/prompts/agent/validator-agent.md 내용
               + open-sdlc-constitution/ 검증 기준
               + open-sdlc-engine/templates/ValidationReportArtifact 템플릿
               + open-sdlc-engine/templates/UseCaseModelArtifact 템플릿 (스키마 참조용)
user_message:  ReqAgent가 생성한 UC artifact(YAML) ← 이것만!
               (ReqAgent의 system prompt, 사고 과정, 중간 응답은 절대 포함하지 않음)
output:        ValidationReportArtifact (YAML) with validation_result: pass|warning|fail
```

### CodeAgent 호출 구조 (ValidatorAgent pass 이후)
```
system_prompt: open-sdlc-engine/prompts/agent/code-agent.md 내용
               + 기술 스택 제약사항
user_message:  승인된 UC artifact(YAML)
output:        ImplementationArtifact (YAML) + 실제 코드 파일
```

### 핵심 금지사항
- Agent A의 system prompt 내용을 Agent B에게 전달하지 않는다
- Agent A의 LLM 응답 중 artifact 이외의 내용(사고 과정, 설명 등)을 Agent B에게 전달하지 않는다
- 하나의 messages.create 호출에서 여러 Agent 역할을 수행하게 하지 않는다

---

## 5. LangGraph 구현 설계

### State 정의
```python
from typing import TypedDict, Literal

class PipelineState(TypedDict):
    user_story: str                          # 원본 사용자 요청
    uc_artifact: str                         # UseCaseModelArtifact YAML
    validation_report: str                   # ValidationReportArtifact YAML
    validation_result: Literal["pass", "warning", "fail"]
    impl_artifact: str                       # ImplementationArtifact YAML
    iteration_count: int                     # 재작업 횟수 (무한루프 방지)
    max_iterations: int                      # 최대 재작업 횟수 (기본 3)
```

### Graph 구조
```python
from langgraph.graph import StateGraph, END

graph = StateGraph(PipelineState)

graph.add_node("req_agent", req_agent_node)
graph.add_node("validator_agent", validator_agent_node)
graph.add_node("code_agent", code_agent_node)

graph.set_entry_point("req_agent")
graph.add_edge("req_agent", "validator_agent")

# 조건부 라우팅: pass → code_agent, fail → req_agent (재작업)
graph.add_conditional_edges(
    "validator_agent",
    route_after_validation,
    {
        "pass": "code_agent",
        "rework": "req_agent",
        "max_retries": END,
    }
)
graph.add_edge("code_agent", END)
```

### 라우팅 함수
```python
def route_after_validation(state: PipelineState) -> str:
    if state["validation_result"] == "pass":
        return "pass"
    if state["iteration_count"] >= state["max_iterations"]:
        return "max_retries"
    return "rework"
```

---

## 6. ValidatorAgent 검증력 강화 전략

단순한 context 격리만으로는 부족할 수 있다. 다음 기법을 적용한다:

### Adversarial Prompting
ValidatorAgent의 system prompt에 다음을 포함:
- "pass를 내기 전에 반드시 fail 사유 후보를 3개 이상 나열하라"
- "그 중 blocking 사유가 하나도 없을 때만 pass로 판정하라"
- "schema 미준수, 누락 필드, 모호한 acceptance criteria는 무조건 fail"

### 체크리스트 강제
v1의 6가지 감사 기준을 항목별로 점검하고 결과를 채우게 한다:
1. schema: 템플릿 필수 필드 모두 존재하는가
2. traceability: source_artifact_ids가 올바르게 참조되는가
3. evidence: 주장에 대한 근거가 있는가
4. decision_consistency: 판정이 논리적으로 일관되는가
5. role_boundary: Agent가 자기 역할 범위를 벗어나지 않았는가
6. no_regression: 기존 통과 항목을 훼손하지 않았는가

---

## 7. 프로젝트 디렉토리 구조

```
open-sdlc-v1/
├── CLAUDE.md                        ← 이 파일 (Claude CLI 컨텍스트)
├── AGENTS.md                        ← 기존 파일 (OpenSDLC Agent 규칙)
├── open-sdlc-constitution/          ← 기존: 거버넌스 규칙
├── open-sdlc-engine/                ← 기존: 방법론 명세
│   ├── core-concepts/
│   ├── prompts/
│   └── templates/
├── open-sdlc-docs/                  ← 기존: 참고 문서
│
├── poc/                             ← 신규: PoC 구현 코드
│   ├── pyproject.toml               # 의존성 관리
│   ├── src/
│   │   ├── graph.py                 # LangGraph 파이프라인 정의
│   │   ├── nodes/
│   │   │   ├── req_agent.py         # ReqAgent 노드
│   │   │   ├── validator_agent.py   # ValidatorAgent 노드
│   │   │   └── code_agent.py        # CodeAgent 노드
│   │   ├── prompts/
│   │   │   ├── loader.py            # 프롬프트/템플릿 파일 로더
│   │   │   └── builder.py           # Agent별 프롬프트 조립기
│   │   ├── artifacts/
│   │   │   ├── parser.py            # YAML artifact 파싱
│   │   │   └── validator.py         # 스키마 검증 유틸
│   │   └── config.py                # LLM 설정, 모델 선택
│   ├── tests/
│   │   ├── test_context_isolation.py # context 격리 검증 테스트
│   │   └── test_validation_quality.py # Validator가 fail을 내는지 테스트
│   └── run_poc.py                   # PoC 실행 엔트리포인트
│
└── workspace/                       ← 런타임 산출물 (gitignore)
```

---

## 8. 구현 순서

### Step 1: 프로젝트 셋업
- `poc/` 디렉토리 생성
- pyproject.toml에 의존성 정의: langgraph, langchain-anthropic, pyyaml
- config.py에 Anthropic API 키 로딩 및 모델 설정

### Step 2: 프롬프트 로더 구현
- `open-sdlc-engine/prompts/agent/` 에서 Agent별 시스템 프롬프트 읽기
- `open-sdlc-engine/templates/` 에서 아티팩트 템플릿 읽기
- `open-sdlc-constitution/` 에서 핵심 원칙 발췌 읽기
- 이들을 조합하여 각 Agent의 최종 system prompt를 빌드하는 builder

### Step 3: ReqAgent 노드 구현
- 독립 LLM API 호출로 UC artifact(YAML) 생성
- 재작업 모드: 이전 UC + fail 사유를 입력으로 받아 개선된 UC 생성

### Step 4: ValidatorAgent 노드 구현
- 독립 LLM API 호출로 ValidationReport(YAML) 생성
- UC artifact만 입력으로 받음 (ReqAgent의 context는 전달하지 않음)
- Adversarial prompting + 체크리스트 강제 적용

### Step 5: LangGraph 파이프라인 연결
- req_agent → validator_agent → 조건부 라우팅(pass/fail)
- fail 시 재작업 루프, max_iterations 초과 시 강제 종료

### Step 6: 검증 테스트
- 의도적으로 모호한 User Story 입력 → fail이 나오는지 확인
- 명확한 User Story 입력 → pass가 나오는지 확인
- fail → 재작업 → pass 루프가 동작하는지 확인

---

## 9. 기존 v1 파일 참조 규칙

구현 시 다음 기존 파일들을 반드시 참조한다:

| 용도 | 경로 |
|------|------|
| Agent 역할 정의 | `open-sdlc-engine/core-concepts/agent-definitions.md` |
| 파이프라인 워크플로우 | `open-sdlc-engine/core-concepts/workflow.md` |
| 핵심 설계 원칙 | `open-sdlc-engine/core-concepts/core-concept.md` |
| Agent별 프롬프트 | `open-sdlc-engine/prompts/agent/` |
| 시스템 프롬프트 | `open-sdlc-engine/prompts/system/` |
| 아티팩트 템플릿 | `open-sdlc-engine/templates/` |
| 헌법 (최상위 규범) | `open-sdlc-constitution/` |

**주의**: 이 파일들의 내용을 임의로 수정하지 않는다.
PoC 코드는 이 파일들을 "읽기 전용 입력"으로 사용하여 프롬프트를 조립한다.

---

## 10. 코딩 규칙

- Python 3.11+ 기준, type hints 필수
- 각 Agent 노드는 순수 함수로 구현 (side effect 없음, state in → state out)
- LLM API 호출은 반드시 `async`로 구현
- YAML 파싱에는 `pyyaml` 사용, 스키마 검증에는 `pydantic` 사용
- 모든 LLM 호출의 입력/출력을 로깅 (디버깅 및 context 격리 검증용)
- 환경변수: `ANTHROPIC_API_KEY`로 API 키 관리
