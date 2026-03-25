# CLAUDE.md — OpenSDLC Implementation Guide

이 파일은 Claude CLI(Claude Code)가 프로젝트 진입 시 자동으로 읽는 컨텍스트 파일이다.
OpenSDLC의 아키텍처, 코드 구조, 개발 규칙을 담고 있다.

---

## 1. 프로젝트 개요

OpenSDLC는 소프트웨어 개발 생명주기(SDLC)의 각 단계를 담당하는 AI Agent들이
구조화된 YAML 아티팩트를 통해 협업하는 **AI Software Factory** 플랫폼이다.

### 핵심 설계 원칙: Context 격리
각 Agent는 **별도의 LLM API 호출**로 실행된다.
Agent 간에 전달되는 것은 오직 **YAML 아티팩트 문자열**뿐이다.
- Agent A의 system prompt 내용을 Agent B에게 전달하지 않는다
- Agent A의 LLM 응답 중 artifact 이외의 내용(사고 과정, 설명 등)을 Agent B에게 전달하지 않는다
- 하나의 LLM 호출에서 여러 Agent 역할을 수행하게 하지 않는다

### 현재 상태
- **PoC 완성** (`poc/`): CLI로 파이프라인을 실행하는 독립 구현체
- **Backend 구현 완료** (`backend/`): FastAPI 서버 — 프로젝트/실행 관리, SSE 실시간 스트리밍, SQLite 영속화, API Key 인증
- **방법론 명세** (`core/`): git submodule, 읽기 전용

---

## 2. 빌드 및 실행

### 가상환경 활성화 (필수)
```bash
source ~/opensdlc-venv/bin/activate
```
> **모든 CLI/테스트/서버 실행 전에 반드시 가상환경을 활성화해야 한다.**

### PoC (CLI)
```bash
cd poc
pip install -e ".[all-llm]"    # 또는 .[anthropic], .[google], .[openai]
cp .env.example .env           # API 키 설정
python run_poc.py --pipeline pipelines/poc_classic.yaml \
  --user-story "할 일 관리 앱을 만들어줘"
```

### Backend (FastAPI)
```bash
cd backend
pip install -e .
python run_server.py --reload   # http://localhost:8000
# POST /api/runs  →  시작
# GET  /api/runs/{id}/events  →  SSE 스트림
```

### 테스트
```bash
cd poc && pytest tests/
cd backend && pytest tests/
```

### 환경변수
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OPENSDLC_LLM_PROVIDER` | `google` | LLM 제공자: `anthropic` / `google` / `openai` |
| `OPENSDLC_MODEL` | 제공자별 기본 | 모델 오버라이드 (예: `claude-sonnet-4-6`) |
| `ANTHROPIC_API_KEY` | | Anthropic API 키 |
| `GOOGLE_API_KEY` | | Google AI API 키 |
| `OPENAI_API_KEY` | | OpenAI API 키 |
| `OPENSDLC_MAX_ITERATIONS` | `3` | 최대 spiral iteration 수 |
| `OPENSDLC_LLM_MAX_RETRIES` | `2` | LLM 품질 재시도 횟수 |
| `OPENSDLC_LOG_LEVEL` | `INFO` | 로깅 레벨 |
| `OPENSDLC_LOG_LLM_IO` | `true` | LLM 입출력 로깅 토글 |
| `OPENSDLC_DATA_DIR` | `backend/data` | DB 및 아티팩트 저장 경로 |
| `OPENSDLC_CORS_ORIGINS` | `*` | CORS 허용 오리진 (쉼표 구분) |
| `OPENSDLC_API_KEY` | (비활성) | API Key 인증 — 빈 문자열이면 인증 비활성 (dev mode) |

---

## 3. 기술 스택

| 구성요소 | 기술 | 비고 |
|----------|------|------|
| Agent 오케스트레이션 | **LangGraph** | StateGraph 기반, 조건부 라우팅(pass/fail) |
| LLM API | **Anthropic / Google / OpenAI** | 멀티 프로바이더 지원, 런타임에 선택 |
| API 서버 | **FastAPI + Uvicorn** | SSE 스트리밍, 비동기 실행 |
| 영속화 | **SQLAlchemy ORM + SQLite** | Project → Run → Iteration → Step → Artifact 계층 |
| 런타임 | **Python 3.11+** | type hints 필수 |
| 데이터 모델 | **Pydantic v2** | AgentConfig, StepDefinition, API 요청/응답 모델 |
| 아티팩트 형식 | **YAML (pyyaml)** | 모든 Agent 입출력 |

---

## 4. 프로젝트 디렉토리 구조

```
openSDLC/
├── CLAUDE.md                           ← 이 파일
├── core/                               ← git submodule (읽기 전용)
│   ├── open-sdlc-constitution/         ← 거버넌스 규칙 (01~05.md)
│   ├── open-sdlc-engine/
│   │   ├── agent-configs/              ← Agent 설정 YAML (*.config.yaml)
│   │   ├── core-concepts/              ← 방법론 명세
│   │   ├── prompts/agent/              ← Agent별 시스템 프롬프트 (.txt)
│   │   └── templates/artifacts/        ← 아티팩트 YAML 템플릿
│   └── open-sdlc-docs/                 ← 참고 문서
│
├── poc/                                ← PoC CLI 구현 (완성)
│   ├── pyproject.toml
│   ├── run_poc.py                      ← CLI 엔트리포인트
│   ├── pipelines/                      ← 파이프라인 정의 YAML
│   │   ├── poc_classic.yaml            ← 3단계: Req→Val→Code
│   │   └── full_spiral.yaml            ← 12단계 full SDLC
│   ├── agent-config-overrides/         ← Agent별 오버레이 설정
│   ├── src/
│   │   ├── config.py                   ← 환경변수, 경로 설정
│   │   ├── llm_client.py              ← 멀티 프로바이더 LLM 클라이언트
│   │   ├── pipeline/
│   │   │   ├── state.py               ← PipelineState TypedDict
│   │   │   ├── graph_builder.py       ← YAML→LangGraph 컴파일러
│   │   │   └── routing.py            ← Validator 조건부 라우팅
│   │   ├── executor/
│   │   │   └── generic_agent.py       ← 범용 Agent 노드 팩토리
│   │   ├── prompts/
│   │   │   ├── loader.py              ← core/ 파일 로더 (캐싱)
│   │   │   ├── builder.py            ← system prompt 조립기
│   │   │   ├── message_strategies.py  ← user message 전략 패턴
│   │   │   └── mandates/             ← 특수 지시문 (adversarial 등)
│   │   ├── artifacts/
│   │   │   ├── parser.py             ← YAML 추출/파싱/복구
│   │   │   └── code_extractor.py     ← 코드 파일 추출
│   │   ├── registry/
│   │   │   ├── models.py             ← AgentConfig, StepDefinition, PipelineDefinition
│   │   │   └── agent_registry.py     ← Agent 설정 로딩/조회
│   │   └── reporting/
│   │       └── event_parser.py       ← Agent 서사 이벤트 파싱
│   └── tests/
│       ├── test_context_isolation.py
│       └── test_validation_quality.py
│
├── backend/                            ← FastAPI 서버
│   ├── pyproject.toml
│   ├── run_server.py                   ← 서버 엔트리포인트
│   ├── pipelines/                      ← 서버용 파이프라인 정의
│   ├── agent-config-overrides/         ← 서버용 Agent 오버레이
│   └── app/
│       ├── main.py                     ← FastAPI 앱 팩토리 (lifespan, CORS, auth)
│       ├── auth.py                     ← API Key 인증 (X-API-Key 헤더)
│       ├── models/                     ← 요청/응답 Pydantic 모델
│       │   ├── requests.py            ← StartRunRequest, CreateProjectRequest 등
│       │   └── responses.py           ← RunDetail, ProgressInfo, RunArtifacts 등
│       ├── routers/                    ← API 엔드포인트
│       │   ├── health.py              ← GET /api/health
│       │   ├── projects.py            ← Project CRUD (POST/GET/PUT/DELETE)
│       │   ├── pipelines.py           ← GET /api/pipelines
│       │   ├── agents.py              ← GET /api/agents
│       │   └── runs.py               ← 실행 관리 (시작/조회/SSE/취소/진행률)
│       ├── services/
│       │   ├── run_manager.py         ← 비동기 파이프라인 실행 + 실시간 DB 영속화
│       │   ├── event_bus.py           ← 스레드-안전 SSE 이벤트 버스
│       │   └── print_capture.py       ← print() → SSE 브릿지 + 취소/아티팩트 콜백
│       ├── db/                         ← SQLAlchemy 영속화 레이어
│       │   ├── models.py             ← ORM 모델 (Project, Run, Iteration, Step, Artifact, CodeFile, Event)
│       │   ├── repository.py         ← CRUD 함수
│       │   └── session.py            ← DB 초기화 + 세션 팩토리
│       └── core/                       ← poc/src/와 동일 구조 (복제)
│           ├── config.py
│           ├── llm_client.py
│           ├── pipeline/
│           ├── executor/
│           ├── prompts/
│           ├── artifacts/
│           ├── registry/
│           └── reporting/
│   └── tests/                          ← Backend 테스트
│       ├── conftest.py                ← 공유 fixture (tmp_db, test_client, authed_client)
│       ├── test_api_endpoints.py      ← API 엔드포인트 통합 테스트
│       ├── test_auth.py              ← API Key 인증 테스트
│       ├── test_event_bus.py         ← EventBus 단위 테스트
│       └── test_print_capture.py     ← 메시지 분류 테스트
│
├── examples/                           ← 사용 예제
└── workspace/                          ← 런타임 산출물 (gitignored)
```

---

## 5. 아키텍처

### 5.1 파이프라인 정의 (YAML-driven)

파이프라인은 `pipelines/*.yaml`에 선언적으로 정의한다. 코드 수정 없이 파이프라인 구성 변경 가능:

```yaml
name: poc-classic
max_iterations: 3
max_reworks_per_gate: 3
steps:
  - step: 1
    agent: ReqAgent
  - step: 2
    agent: ValidatorAgent
    on_fail: ReqAgent          # fail 시 rework 대상
  - step: 3
    agent: CodeAgent
    max_tokens: 16384
```

`graph_builder.py`가 YAML을 LangGraph `StateGraph`로 컴파일한다.

### 5.2 Agent 실행 흐름

```
PipelineDefinition (YAML)
  → graph_builder: StepDefinition마다 create_agent_node() 호출
    → generic_agent.py: Agent 노드 클로저 생성
      1. 취소 체크: cancel_event가 설정되면 InterruptedError 발생
      2. [__OPENSDLC_STEP_START__] 마커 출력 → EventBus로 STEP_STARTED 전파
      3. agent_registry에서 AgentConfig 로딩 (core/ + overrides 병합)
      4. builder.py로 system prompt 조립
      5. message_strategies.py로 user message 구성
      6. llm_client.call_llm()으로 LLM 호출 (context 격리)
      7. artifacts/parser.py로 응답 파싱 (narrative + YAML 분리)
      8. artifact_saver 콜백으로 실시간 디스크/DB 저장
      9. [__OPENSDLC_STEP_END__] 마커 출력 (JSON 인코딩된 step 결과)
     10. PipelineState 업데이트 반환
```

### 5.3 Agent 목록 (6종)

| Agent | 역할 | 출력 아티팩트 |
|-------|------|---------------|
| PMAgent | 프로젝트 관리, iteration 평가 | iteration_assessment |
| ReqAgent | 요구사항 분석 | UseCaseModelArtifact |
| ValidatorAgent | 아티팩트 검증 (게이트) | ValidationReportArtifact |
| CodeAgent | 코드 구현 | ImplementationArtifact |
| TestAgent | 테스트 설계/실행 (dual mode) | TestDesignArtifact / TestReportArtifact |
| CoordAgent | 이터레이션 피드백 | FeedbackArtifact |

Agent 설정은 `core/open-sdlc-engine/agent-configs/*.config.yaml`에 정의되고,
`poc/agent-config-overrides/` (또는 `backend/agent-config-overrides/`)로 오버레이된다.

### 5.4 LLM 호출 구조

`llm_client.py`는 3개 프로바이더를 통합한다:
- **Anthropic**: 프롬프트 캐싱 (`cache_control: ephemeral`)
- **Google (Gemini)**: `CachedContent` API 활용
- **OpenAI**: 표준 chat completions

공통 기능: 품질 검사 (최소 응답 길이), rate-limit 자동 재시도, 일일 quota 탐지.

### 5.5 ValidatorAgent 강화

- **Adversarial prompting** (`adversarial_mandate.md`): "pass 전 fail 후보 3개 나열" 강제
- **Context 격리**: artifact YAML만 전달, 이전 agent의 사고 과정 미포함
- **체크리스트 강제**: schema, traceability, evidence, decision_consistency, role_boundary, no_regression

### 5.6 Backend API

#### 인증
`OPENSDLC_API_KEY` 환경변수가 설정되면 `X-API-Key` 헤더 기반 인증이 활성화된다.
빈 문자열(기본값)이면 인증 비활성 (dev mode). Health 엔드포인트는 인증 불요.
타이밍 안전 비교(`secrets.compare_digest`) 사용.

#### 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health` | 헬스체크 + 현재 LLM 설정 (인증 불요) |
| **프로젝트** | | |
| POST | `/api/projects` | 프로젝트 생성 |
| GET | `/api/projects` | 프로젝트 목록 |
| GET | `/api/projects/{id}` | 프로젝트 상세 (소속 Run 포함) |
| PUT | `/api/projects/{id}` | 프로젝트 수정 |
| DELETE | `/api/projects/{id}` | 프로젝트 삭제 |
| **파이프라인/에이전트** | | |
| GET | `/api/pipelines` | 사용 가능한 파이프라인 목록 |
| GET | `/api/pipelines/{name}` | 파이프라인 상세 (steps 포함) |
| GET | `/api/agents` | 등록된 Agent 목록 |
| GET | `/api/agents/{agent_id}` | Agent 상세 |
| **실행 관리** | | |
| POST | `/api/runs` | 파이프라인 실행 시작 (비동기, project_id 선택) |
| GET | `/api/runs` | 실행 목록 (project_id 필터 지원) |
| GET | `/api/runs/{id}` | 실행 상세 (iteration/step/artifact 트리) |
| GET | `/api/runs/{id}/events` | SSE 실시간 이벤트 스트림 (완료 후 DB 리플레이) |
| GET | `/api/runs/{id}/artifacts` | 산출물 (YAML + 코드 파일, iteration 필터) |
| GET | `/api/runs/{id}/progress` | 진행률 폴링 (현재 iteration/step/agent) |
| POST | `/api/runs/{id}/cancel` | 실행 취소 요청 (202, 현재 step 완료 후 중단) |

### 5.7 Backend 내부 아키텍처

#### 실행 생명주기 (`RunManager`)
1. `start_run()`: DB에 Run 생성 → `asyncio.to_thread`로 동기 LangGraph를 비동기 래핑
2. 파이프라인 스레드에서 `capture_prints()` 컨텍스트로 print() 출력 가로채기
3. 각 print 메시지 → `classify_print_message()` → `EventBus.emit()` → SSE 스트림
4. 완료/실패 시 DB 상태 업데이트 + `EventBus.close()` → SSE 연결 종료

#### 실시간 DB 영속화
- **`on_emit` 콜백**: `STEP_STARTED` → Iteration/Step DB 행 생성, `STEP_COMPLETED` → Step 행 업데이트 (토큰, 모델, verdict)
- **`artifact_saver` 콜백**: `generic_agent.py`에서 직접 호출 — 아티팩트 YAML을 디스크에 저장, Artifact DB 행 삽입, ImplementationArtifact인 경우 코드 파일 추출
- 두 콜백은 `_make_run_callbacks()`에서 동일한 `step_counter_per_iter` dict를 공유하여 정확한 step 번호 추적

#### Print 마커 프로토콜
LLM 출력과의 충돌을 방지하기 위해 `__OPENSDLC_` 네임스페이스 접두사 사용:
- `[__OPENSDLC_STEP_START__] step_num=N agent=AgentId iteration=N output=ArtifactType`
- `[__OPENSDLC_STEP_END__] {JSON}`

#### 취소 메커니즘
`threading.Event`를 thread-local에 저장 → `generic_agent.py`가 각 step 시작 시 체크 → 설정 시 `InterruptedError` → `RunManager`가 `CANCELLED` 상태로 DB 업데이트

#### EventBus
- `emit()`: 동기 스레드에서 호출, `loop.call_soon_threadsafe`로 async 이벤트 루프에 통지
- `subscribe()`: 비동기 제너레이터, `poll_interval` (기본 5초) 타임아웃으로 SSE 연결 끊김 감지
- `close()` 호출 후 모든 이벤트 전달 완료 시 SSE 스트림 자연 종료

---

## 6. 핵심 데이터 모델

### PipelineState (LangGraph state)
```python
class PipelineState(TypedDict):
    user_story: str                      # 원본 사용자 요청
    steps_completed: list[StepResult]    # 실행된 step 이력
    latest_artifacts: dict[str, str]     # artifact_type → 최신 YAML
    current_step_index: int              # 현재 step 위치
    iteration_count: int                 # spiral iteration 번호
    max_iterations: int                  # 최대 spiral 반복
    rework_count: int                    # 현재 gate의 rework 횟수
    max_reworks_per_gate: int            # gate당 최대 rework
    pipeline_status: str                 # running|completed|max_retries_exceeded
```

### 설정 모델 (Pydantic)
- `AgentConfig`: Agent 설정 (persona, prompts, inputs/outputs, overrides)
- `StepDefinition`: 파이프라인 단계 (agent, model, on_fail, mode 등)
- `PipelineDefinition`: 파이프라인 전체 (name, steps, limits)

### DB 모델 (SQLAlchemy ORM)
```
Project ─1:N─ Run (UserStory) ─1:N─ Iteration ─1:N─ Step ─1:N─ Artifact
                                                ↘ CodeFile
                               ↘ Event
```

| 테이블 | 주요 컬럼 | 설명 |
|--------|-----------|------|
| `projects` | project_id, name, description | 프로젝트 (Run 그룹) |
| `runs` | run_id, pipeline_name, user_story, status, project_id | 파이프라인 실행 |
| `iterations` | run_id, iteration_num, status, satisfaction_score | Spiral 반복 |
| `steps` | run_id, iteration_num, step_num, agent_name, verdict, model_used, 토큰 사용량 | Agent 단계 실행 |
| `artifacts` | artifact_type, artifact_id, file_path | YAML 아티팩트 (디스크 경로 참조) |
| `code_files` | relative_path, file_path, size_bytes | 추출된 코드 파일 |
| `events` | event_type, agent_name, message, data(JSON) | SSE 이벤트 이력 |

---

## 7. core/ submodule 참조 규칙

| 용도 | 경로 |
|------|------|
| Agent 역할 정의 | `core/open-sdlc-engine/core-concepts/agent-definitions.md` |
| 파이프라인 워크플로우 | `core/open-sdlc-engine/core-concepts/workflow.md` |
| 핵심 설계 원칙 | `core/open-sdlc-engine/core-concepts/core-concept.md` |
| Agent 설정 파일 | `core/open-sdlc-engine/agent-configs/*.config.yaml` |
| Agent별 프롬프트 | `core/open-sdlc-engine/prompts/agent/*.txt` |
| 아티팩트 템플릿 | `core/open-sdlc-engine/templates/artifacts/*.yaml` |
| 헌법 (거버넌스) | `core/open-sdlc-constitution/01~05-*.md` |

**절대 수정 금지**: core/ 내 파일을 임의로 수정하지 않는다.
코드는 이 파일들을 "읽기 전용 입력"으로 사용하여 프롬프트를 조립한다.

---

## 8. 코딩 규칙

- Python 3.11+, type hints 필수
- Agent 노드는 순수 함수: `PipelineState → dict` (부분 state 업데이트)
- LLM 호출은 `llm_client.call_llm()` 통해서만 수행 (동기, 프로바이더 추상화)
- YAML 파싱: `pyyaml`, 스키마: `pydantic v2`
- 모든 LLM 입출력 로깅 (context 격리 검증용)
- Agent별 로직은 if/elif 분기가 아닌 **config-driven + strategy pattern** 사용
  - system prompt: `builder.py` (AgentConfig 기반 조립)
  - user message: `message_strategies.py` (strategy key로 디스패치)
- `poc/` 와 `backend/app/core/`는 현재 코드 복제 관계 — 향후 패키지 통합 예정
- **테스트 코드는 자동 생성하지 않는다** — 사용자가 명시적인 프롬프트로 테스트 파일 생성 및 실행을 지시한 경우에 한해서만 수행한다. 코드 변경 시 기존 테스트 자동 실행도 금지하며, 사용자가 명시적으로 요청한 경우에만 진행한다.

---

## 9. 파이프라인 확장 가이드

### 새 Agent 추가
1. `core/open-sdlc-engine/agent-configs/`에 `{AgentId}.config.yaml` 확인
2. `poc/agent-config-overrides/`에 `{AgentId}.override.yaml` 작성 (constitution_sections, mandate_files, user_message_strategy)
3. 필요 시 `message_strategies.py`에 전략 함수 추가
4. `pipelines/*.yaml`에 step 추가

### 새 파이프라인 정의
`pipelines/` 디렉토리에 YAML 파일 추가 — 기존 Agent를 조합하여 새 워크플로우 구성.
`on_fail`로 ValidatorAgent의 rework 대상을 지정한다.

### 새 LLM 프로바이더 추가
`llm_client.py`에 `_call_{provider}()` 함수 추가 후 `_PROVIDERS` dict에 등록.
