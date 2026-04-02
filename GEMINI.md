# GEMINI.md - OpenSDLC 구현 및 개발 가이드

이 파일은 Gemini CLI가 프로젝트 작업 시 준수해야 할 핵심 지침, 아키텍처, 코드 구조 및 개발 규칙을 담고 있는 컨텍스트 파일이다.
OpenSDLC 방법론을 코드로 구현하는 과정에서 일관성, 품질, 그리고 핵심 원칙(컨텍스트 격리)을 유지하기 위해 이 규칙을 엄격히 따른다.

---

### 가상환경 활성화 (필수)
```bash
source ~/opensdlc-venv/bin/activate
```
> **모든 CLI/테스트/서버 실행 전에 반드시 가상환경을 활성화해야 한다.**

## 1. 프로젝트 개요

OpenSDLC는 소프트웨어 개발 생명주기(SDLC)의 각 단계를 담당하는 AI Agent들이 구조화된 YAML 아티팩트를 통해 협업하는 **AI Software Factory** 플랫폼이다.

### 핵심 설계 원칙: 컨텍스트 격리 (Context Isolation)
각 Agent는 반드시 **별도의 LLM API 호출**로 실행되어야 한다.
Agent 간에 전달되는 것은 오직 **YAML 아티팩트 문자열**뿐이다.
- Agent A의 시스템 프롬프트 내용을 Agent B에게 절대 전달하지 않는다.
- Agent A의 LLM 응답 중 아티팩트 이외의 내용(사고 과정, 설명 등)을 Agent B에게 전달하지 않는다.
- 하나의 LLM 호출에서 여러 Agent 역할을 수행하게 하지 않는다.

### 현재 상태
- **Backend 구현 완료** (`backend/`): FastAPI 서버 — 프로젝트/실행 관리, SSE 실시간 스트리밍, SQLite 영속화, API Key 인증
- **방법론 명세** (`core/`): git submodule, 읽기 전용 (절대 수정 금지)

---

## 2. 빌드 및 실행 지침

### 가상환경 활성화 (필수)
```bash
source ~/opensdlc-venv/bin/activate
```
> **주의:** 모든 CLI, 테스트, 서버 실행 전에 반드시 가상환경을 활성화해야 한다.

### PoC (CLI)
```bash
cd poc
pip install -e ".[all-llm]"    # 또는 .[anthropic], .[google], .[openai]
cp .env.example .env           # API 키 설정 (필요 시)
python run_poc.py --pipeline pipelines/poc_classic.yaml \
  --user-story "요청 내용"
```

### Backend (FastAPI)
```bash
cd backend
pip install -e .
python run_server.py --reload   # http://localhost:8000
# POST /api/runs  →  시작
# GET  /api/runs/{id}/events  →  SSE 스트림
```

### 테스트 실행
```bash
# PoC (핵심 원칙 검증 등 포함)
cd poc && pytest tests/
# Backend
cd backend && pytest tests/
```

### 환경 변수
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OPENSDLC_LLM_PROVIDER` | `google` | LLM 제공자: `google` / `anthropic` / `openai` |
| `OPENSDLC_MODEL` | 제공자별 기본 | 모델 오버라이드 (예: `gemini-2.5-pro`) |
| `GOOGLE_API_KEY` | | Google AI API 키 |
| `ANTHROPIC_API_KEY` | | Anthropic API 키 |
| `OPENAI_API_KEY` | | OpenAI API 키 |
| `OPENSDLC_MAX_ITERATIONS` | `3` | 최대 spiral iteration 수 |
| `OPENSDLC_LLM_MAX_RETRIES` | `2` | LLM 품질 재시도 횟수 |
| `OPENSDLC_LOG_LEVEL` | `INFO` | 로깅 레벨 |
| `OPENSDLC_LOG_LLM_IO` | `true` | LLM 입출력 로깅 토글 |
| `OPENSDLC_DATA_DIR` | `backend/data` | DB 및 아티팩트 저장 경로 |
| `OPENSDLC_CORS_ORIGINS` | `*` | CORS 허용 오리진 (쉼표 구분) |
| `OPENSDLC_API_KEY` | (비활성) | 백엔드 API 인증 키 (빈 값일 경우 인증 비활성화 - dev mode) |

---

## 3. 기술 스택

| 구성요소 | 기술 | 비고 |
|----------|------|------|
| Agent 오케스트레이션 | **LangGraph** | StateGraph 기반, 조건부 라우팅(pass/fail) |
| LLM API | **Google / Anthropic / OpenAI** | 멀티 프로바이더 지원 |
| API 서버 | **FastAPI + Uvicorn** | SSE 스트리밍, 비동기 실행 |
| 영속화 | **SQLAlchemy ORM + SQLite** | Project → Run → Iteration → Step → Artifact 계층 |
| 런타임 | **Python 3.11+** | Type Hints 필수 |
| 데이터 모델 | **Pydantic v2** | AgentConfig, StepDefinition, API 요청/응답 모델 |
| 아티팩트 형식 | **YAML (PyYAML)** | 모든 Agent 입출력 |

---

## 4. 핵심 디렉토리 구조 및 역할

- `core/`: 방법론 명세, 헌법, 템플릿 등 (git submodule, **읽기 전용**)
- `poc/`: PoC CLI 구현체. LLM 파이프라인 컴파일 및 실행. (`src/` 내 핵심 로직)
- `backend/`: FastAPI 기반 서버. `app/core/`는 `poc/src/`와 현재 동일한 구조를 가지며, API 라우팅, DB 통신, 실시간 이벤트 버스 추가.
- `workspace/`: 런타임 산출물 저장소 (gitignored).

---

## 5. 아키텍처 및 구현 상세

### 5.1 파이프라인 정의 (YAML-driven)
`pipelines/*.yaml`에 선언적으로 정의하며, `graph_builder.py`가 이를 LangGraph `StateGraph`로 컴파일한다. 코드 수정 없이 워크플로우를 변경할 수 있다.

### 5.2 Agent 실행 흐름 및 노드 구현
- 노드는 `PipelineState`를 입력받아 부분 업데이트 `dict`를 반환하는 **순수 함수**로 작성한다.
- LLM 호출은 반드시 `llm_client.call_llm()`을 통해 수행 (Context 격리 보장).
- 하드코딩을 지양하고 **Config-driven + Strategy pattern**을 사용:
  - 프롬프트 조립: `builder.py` (core/ 내 파일 동적 결합)
  - 사용자 메시지 생성: `message_strategies.py`

### 5.3 ValidatorAgent 강화
- **Adversarial Prompting**: 'Pass' 판정 전 반드시 실패 사유 후보를 3개 이상 도출하도록 강제 (`adversarial_mandate.md`).
- **6대 품질 게이트**: 스키마, 추적성, 근거, 논리적 일관성, 역할 경계, 회귀 방지.

### 5.4 런타임 이벤트 및 통신
- 실시간 이벤트는 **SSE (Server-Sent Events)**(`EventBus`)를 통해 스트리밍된다.
- LLM 출력과 시스템 메시지의 충돌을 막기 위해 런타임 마커 프로토콜(`__OPENSDLC_STEP_START__`, `__OPENSDLC_STEP_END__`)을 사용한다.
- 아티팩트 및 코드는 `artifact_saver` 콜백을 통해 실시간으로 디스크/DB에 영속화된다.

### 5.5 Backend DB 모델 (SQLAlchemy)
- `Project` ─1:N─ `Run` (UserStory 포함) ─1:N─ `Iteration` ─1:N─ `Step` ─1:N─ `Artifact` (YAML) & `CodeFile` (추출된 코드)
- `Event` 테이블을 통해 SSE 이벤트 이력 저장.

---

## 6. core/ 서브모듈 참조 규칙 (읽기 전용)

다음 경로의 파일들은 방법론의 근간이므로 **절대 직접 수정하지 않는다**. 코드는 이 파일들을 읽어 프롬프트와 설정을 동적으로 조립한다. 모든 변경 사항은 `poc/` 또는 `backend/` 내의 오버라이드 설정을 통해 반영한다.

- 에이전트 역할 정의: `core/open-sdlc-engine/core-concepts/agent-definitions.md`
- 워크플로우/핵심원칙: `core/open-sdlc-engine/core-concepts/workflow.md`, `core-concept.md`
- 설정 및 프롬프트: `core/open-sdlc-engine/agent-configs/*.config.yaml`, `prompts/agent/*.txt`
- 아티팩트 템플릿: `core/open-sdlc-engine/templates/artifacts/*.yaml`
- 최상위 규범(헌법): `core/open-sdlc-constitution/01~05-*.md`
