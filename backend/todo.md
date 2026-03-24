## 기능 요구사항 달성 분석

### 요구사항별 판정

---

#### 1. 프로젝트 CRUD — **달성**

| 기능 | Endpoint | 상태 |
|------|----------|------|
| 생성 | `POST /api/projects` | 구현됨 |
| 목록 | `GET /api/projects` | 구현됨 |
| 상세 | `GET /api/projects/{id}` | 구현됨 (하위 run 포함) |
| 수정 | `PUT /api/projects/{id}` | 구현됨 |
| 삭제 | `DELETE /api/projects/{id}` | 구현됨 (run은 보존, project_id=NULL) |

---

#### 2. 유저 스토리 조회 — **부분 달성**

현재 "유저 스토리" = `Run` 테이블의 `user_story` 필드입니다.

| 기능 | 상태 | 비고 |
|------|------|------|
| 프로젝트 하위로 조회 | `GET /api/runs?project_id=X` | 동작함 |
| 프로젝트 상세에서 run 목록 | `GET /api/projects/{id}` → `runs[]` | 동작함 |
| 유저 스토리 개별 조회 | `GET /api/runs/{id}` | `user_story` 필드 포함 |

**갭**: 현재 `POST /api/runs`가 **유저 스토리 생성과 실행을 동시에** 수행합니다. "유저 스토리를 먼저 등록하고 나중에 실행"하는 분리된 흐름이 없습니다. 하지만 현재 SDLC 파이프라인 특성상 유저 스토리 = 실행 트리거이므로 현재 구조가 합리적입니다.

---

#### 3. Iteration 조회 — **부분 달성 (핵심 갭 있음)**

| 기능 | 상태 | 비고 |
|------|------|------|
| 완료된 run의 iteration tree | `GET /api/runs/{id}` → `iterations[]` | DB에서 조회, 동작함 |
| **실행 중인 run의 iteration 정보** | **미동작** | **DB에 아직 없음** |

**핵심 갭**: `_persist_completed_run()`은 **전체 파이프라인 완료 후에만** iteration/step/artifact를 DB에 저장합니다 (`run_manager.py:177-180`). 따라서:

- 파이프라인이 실행 중일 때 `GET /api/runs/{id}` → `iterations: []` (빈 배열)
- 완료 후에야 iteration tree가 채워짐

**요구사항 3, 6 위반** — 사용자가 실행 중에 iteration 진행 상황을 조회할 수 없습니다.

---

#### 4. Pipeline log / Agent log / YAML / Dashboard — **부분 달성**

| 하위 기능 | Endpoint | 상태 |
|-----------|----------|------|
| SSE 실시간 이벤트 | `GET /api/runs/{id}/events` (active) | SSE 스트림 동작 |
| 완료 run 이벤트 replay | `GET /api/runs/{id}/events` (completed) | DB에서 조회 |
| 아티팩트 YAML 조회 | `GET /api/runs/{id}/artifacts` | 동작 (완료 run: 디스크, 실행 중: in-memory fallback) |
| 코드 파일 조회 | `GET /api/runs/{id}/artifacts` → `code_files[]` | 동작 |
| **Agent별 대화 로그 필터** | `GET /api/runs/{id}/events?agent_name=X` | DB replay만 지원, 실행 중 미지원 |
| **현재 Step Dashboard** | **미구현** | **별도 endpoint 없음** |

**갭**: "현재 어떤 Step이 진행 중인지"를 즉시 알 수 있는 endpoint가 없습니다. SSE를 구독해야만 `STEP_STARTED` 이벤트를 통해 추론 가능합니다.

---

#### 5. Agent 순서/모델 지정 (Pipeline 편집) — **달성**

| 기능 | Endpoint | 상태 |
|------|----------|------|
| 파이프라인 생성 | `POST /api/pipelines` | 구현됨 + 자동 on_fail 추론 |
| 목록/상세 조회 | `GET /api/pipelines`, `GET /api/pipelines/{name}` | 구현됨 |
| 수정 | `PUT /api/pipelines/{name}` | 구현됨 (partial update) |
| 삭제 | `DELETE /api/pipelines/{name}` | 구현됨 (default 보호) |
| Agent별 모델 지정 | `steps[].model`, `steps[].provider` | 구현됨 |
| 유효성 검증 | `validate_pipeline_request()` | 구현됨 (agent 존재, TestAgent mode, Validator 위치) |

---

#### 6. 실시간 진행 상황 조회 — **부분 달성 (핵심 갭 있음)**

| 기능 | 상태 | 비고 |
|------|------|------|
| Run status (running/completed) | `GET /api/runs/{id}` → `status` | 동작 (in-memory run 우선) |
| SSE 이벤트 스트림 | `GET /api/runs/{id}/events` | 동작 |
| **현재 iteration/step 번호** | **미구현** | SSE `STEP_STARTED`에 정보는 있지만 polling 조회 불가 |
| **SSE 클라이언트 disconnect 감지** | **미구현** | `request.is_disconnected()` 체크 없음 |

---

#### 7. Agent 독립 Context — **달성**

코드 추적 결과 확인:

- `generic_agent.py:108-115` — 각 Agent가 **독립적인 `call_llm()` 호출**로 실행
- `builder.py:24-100` — system prompt는 `AgentConfig` 기반으로 조립 (Agent별 프롬프트 + Constitution + mandate)
- `create_agent_node()` — 클로저로 각 step의 `system_prompt`가 **빌드 타임에 고정** → 다른 Agent의 prompt와 격리
- Constitution과 Engine의 역할 정의가 system prompt에 포함됨

---

#### 8. Agent 간 아티팩트 격리 — **달성**

코드 추적 결과 확인:

- `_strategy_validator()` (`message_strategies.py:32-49`) — **artifact YAML만** 전달, "이 artifact 외의 정보는 참조하지 말 것" 명시
- `_strategy_req_agent()` — ValidationReport + 이전 artifact만 전달
- `_strategy_input_assembler()` — `primary_inputs`로 지정된 artifact만 전달
- `_strategy_test_agent()` — 관련 artifact만 전달
- Agent의 narrative(사고 과정)는 **절대 다음 Agent에게 전달되지 않음** — `split_narrative_and_yaml()`로 분리 후 `artifact_yaml`만 `latest_artifacts`에 저장

---

### 보완 추천사항 (우선순위순)

#### 1. **실시간 Iteration/Step DB 기록** (Critical — 요구사항 3, 6 위반)

현재 `_persist_completed_run()`이 **완료 후 일괄 저장**하는 구조입니다. 이를 **step 완료 시 즉시 DB 기록**으로 변경해야 합니다.

방법: `generic_agent.py`의 `[__STEP_START__]` 마커를 EventBus에서 수신할 때 DB에 iteration/step을 즉시 insert하고, step 완료 시 update. `_persist_completed_run()`은 최종 정리(artifact 파일 저장, code file 추출)만 담당.

이렇게 하면:
- `GET /api/runs/{id}` 요청 시 **실행 중에도** iteration/step tree가 보임
- 서버 크래시 시에도 진행된 step까지는 DB에 남음

#### 2. **현재 진행 상황 snapshot endpoint** (High — 요구사항 6)

SSE를 구독하지 않고도 현재 상태를 polling할 수 있는 endpoint:

```
GET /api/runs/{id}/progress
→ { current_iteration: 2, current_step: 5, current_agent: "CodeAgent", 
    elapsed_seconds: 45, steps_total: 12 }
```

EventBus의 최신 `STEP_STARTED` 이벤트에서 추출 가능합니다.

#### 3. **SSE disconnect 감지** (Medium)

`runs.py:207-209`의 `event_generator()`에 클라이언트 연결 끊김 체크가 없습니다:

```python
async def event_generator():
    async for idx, event in active.event_bus.subscribe(last_index=last_event_id):
        if await request.is_disconnected():
            break
        yield event.to_sse(event_id=idx)
```

#### 4. **Active run 메모리 정리** (Medium)

`run_manager.py`의 `_active_runs` dict에서 완료된 run이 제거되지 않습니다. `_execute_run`의 `finally` 블록에 추가:

```python
finally:
    record.event_bus.close()
    del self._active_runs[record.run_id]  # ← 추가
```

#### 5. **Run 취소 API** (Medium)

`POST /api/runs/{id}/cancel` — LLM 호출 비용 제어용. `threading.Event` 기반 cancellation flag를 step 간에 체크.

#### 6. **CORS 환경변수화** (Low)

`main.py:53`의 `allow_origins=["*"]`를 환경변수로 분리.

---

### 요약 매트릭스

| # | 요구사항 | 판정 | 핵심 갭 |
|---|---------|------|---------|
| 1 | 프로젝트 CRUD | **달성** | — |
| 2 | 유저 스토리 조회 | **달성** | 생성/실행 분리 없음 (현재 구조 합리적) |
| 3 | Iteration 조회 | **부분** | 실행 중 iteration 정보 없음 (완료 후에만) |
| 4 | 로그/대화/YAML/Dashboard | **부분** | 현재 Step dashboard endpoint 없음 |
| 5 | Pipeline 편집 | **달성** | — |
| 6 | 실시간 진행 상황 | **부분** | polling 조회 불가, SSE만 가능 |
| 7 | Agent 독립 Context | **달성** | — |
| 8 | 아티팩트 격리 | **달성** | — |

**최우선 과제**: 보완 1번(실시간 DB 기록) 하나만 해결하면 요구사항 3, 4, 6의 갭이 동시에 해소됩니다.