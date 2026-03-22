# OpenSDLC PoC 실행 흐름 상세 설명

이 문서는 사용자가 User Story를 입력하고 `run_poc.py`가 동작하는 순간부터,
어떤 파일의 어떤 함수가 어떤 순서로 호출되는지를 차근차근 추적한 것이다.

> 기준 파이프라인: `poc_classic.yaml` (ReqAgent → ValidatorAgent → CodeAgent)
>
> full_spiral.yaml (9단계 전체 파이프라인)은 [Phase 5: full_spiral 파이프라인](#phase-5-full_spiral-파이프라인) 참조

---

## UML 다이어그램 참조

`poc/docs/uml/` 디렉토리에 4종의 PlantUML 다이어그램이 있다.

| 파일 | 종류 | 내용 |
|------|------|------|
| `poc_architecture.puml` | 컴포넌트 다이어그램 | 모듈 간 의존관계 전체 (config.py, multi-provider, mandates 포함) |
| `poc_sequence.puml` | 시퀀스 다이어그램 | poc_classic 실행 흐름, Phase 1~5, LLM retry 상세 |
| `poc_activity.puml` | 액티비티 다이어그램 | full_spiral 전체 파이프라인 플로우, 조건부 라우팅 |
| `poc_state.puml` | 상태 다이어그램 | PipelineState 전이 (Booting → Running → Saving/Failed) |

---

## 명령어 예시

```bash
python run_poc.py -p pipelines/poc_classic.yaml -s "로또 번호 생성기" -o output/
```

---

## Phase 1: 부팅 및 설정 로딩

**`run_poc.py:174` → `main()`**

```
① run_poc.py:10       sys.path에 src/ 추가
② run_poc.py:12       config.py 임포트 (모듈 로드 시점에 실행)
   └─ config.py:8     load_dotenv() → .env 파일에서 환경변수 로드
   └─ config.py:11-17 PROJECT_ROOT, ENGINE_DIR, CONSTITUTION_DIR,
                       PROMPTS_DIR, TEMPLATES_DIR 경로 설정
   └─ config.py:20    LLM_PROVIDER = "google" | "anthropic" | "openai" 결정
                       (OPENSDLC_LLM_PROVIDER 환경변수, 기본값 "google")
   └─ config.py:28-33 각 프로바이더 기본 모델 결정:
                         anthropic → claude-sonnet-4-6
                         google    → gemini-2.5-flash
                         openai    → gpt-4o
                       MODEL = OPENSDLC_MODEL 환경변수 or 기본값
   └─ config.py:36-43 LLM_MAX_RETRIES=2, LOG_LEVEL="INFO", LOG_LLM_IO=true
③ run_poc.py:96       setup_logging() → 로깅 설정
④ run_poc.py:127-138  API 키 유효성 검증 (없으면 exit)
⑤ run_poc.py:145-149  --user-story에서 사용자 입력 읽기
```

---

## Phase 2: 파이프라인 정의 로딩

**`run_poc.py:158` → `load_pipeline_definition()`**

```
⑥ graph_builder.py:21-25  load_pipeline_definition()
   └─ pipelines/poc_classic.yaml 읽기
   └─ PipelineDefinition(**raw) → Pydantic 모델로 파싱
       └─ models.py:47-52   PipelineDefinition(name, steps: list[StepDefinition])
       └─ models.py:34-44   각 step → StepDefinition(step=1, agent="ReqAgent", ...)
```

파싱 결과:

```
PipelineDefinition(
  name="poc-classic",
  max_iterations=3,
  steps=[
    StepDefinition(step=1, agent="ReqAgent"),
    StepDefinition(step=2, agent="ValidatorAgent", on_fail="ReqAgent"),
    StepDefinition(step=3, agent="CodeAgent", max_tokens=16384),
  ]
)
```

---

## Phase 3: 그래프 빌드 (LangGraph 구성)

**`run_poc.py:162` → `run_pipeline()` → `create_pipeline()`**

```
⑦ graph_builder.py:102-115  run_pipeline() — 초기 PipelineState 생성
   └─ state.py:18-26         PipelineState TypedDict 구조:
                              {user_story, steps_completed=[], latest_artifacts={},
                               iteration_count=0, max_iterations=3, ...}

⑧ graph_builder.py:96-99    create_pipeline()
   └─ graph_builder.py:28    build_graph_from_definition() 진입
```

### 3-1. 노드 등록 루프

**`graph_builder.py:28-93` — 각 step마다 반복:**

```
Step 1 (ReqAgent):
  ⑨  graph_builder.py:50   create_agent_node(step) 호출
      └─ generic_agent.py:122-194  create_agent_node() 팩토리
         ├─ agent_registry.py:53   get_agent("ReqAgent") → AgentConfig 로드
         │   └─ agent_registry.py:19  load_all_agents() (최초 1회)
         │       └─ open-sdlc-engine/agent-configs/ReqAgent.config.yaml 파싱
         │       └─ (나머지 Agent config도 전부 로드, lru_cache로 캐싱)
         ├─ builder.py:95          build_system_prompt(agent_config, step)
         │   └─ loader.py:19      load_common_prompt() → AgentCommon.txt 읽기
         │   └─ loader.py:10      load_agent_prompt("ReqAgent") → ReqAgent.txt 읽기
         │   └─ loader.py:25      load_template("UseCaseModelArtifact") → 템플릿 YAML 읽기
         │   └─ loader.py:34      load_constitution_excerpt() → constitution/*.md 읽기
         │   → 이 모든 텍스트를 조합한 system_prompt 문자열 반환
         └─ 클로저 함수 node_fn 반환 (아직 실행 안 됨)
  ⑩  graph_builder.py:51   graph.add_node("step_1_ReqAgent", node_fn)

Step 2 (ValidatorAgent):
  ⑪  같은 과정, 단 builder.py에서 추가로:
      - builder.py:129-136 _VALIDATOR_REFERENCE_TEMPLATES (5종) 스키마 참조 주입:
        UseCaseModelArtifact, TestDesignArtifact, ImplementationArtifact,
        TestReportArtifact, FeedbackArtifact
      - builder.py:150-152 _ADVERSARIAL_MANDATE 주입:
        "List at least 3 potential failure candidates,
         state BLOCKER/NOT, pass only if ZERO blockers remain"
  ⑫  graph.add_node("step_2_ValidatorAgent", node_fn)

Step 3 (CodeAgent):
  ⑬  같은 과정, 단 builder.py:154-157에서 _CODE_FILE_MANDATE 주입:
      "code_files 필드 필수, 완전한 실행 코드 포함,
       code_files[].content는 생략·플레이스홀더 금지"
  ⑭  graph.add_node("step_3_CodeAgent", node_fn)
```

### 3-2. 엣지 연결

```
⑮  step_1_ReqAgent → step_2_ValidatorAgent           (단순 엣지)

⑯  step_2_ValidatorAgent → 조건부 엣지:
    └─ routing.py:12  make_validator_router(step_num=2, max_iterations=3)
       └─ 클로저 route_after_validation 반환
    └─ graph_builder.py:79-87
       "pass"        → step_3_CodeAgent
       "rework"      → step_1_ReqAgent    (← 재작업 루프!)
       "max_retries" → END

⑰  step_3_CodeAgent → END                            (단순 엣지)
```

### 3-3. 컴파일

```
⑱  graph_builder.py:99   graph.compile() → LangGraph 실행 가능 객체
```

---

## Phase 4: 파이프라인 실행 (LLM 호출 시작)

**`graph_builder.py:130` → `compiled.invoke(initial_state)`**

LangGraph가 entry point부터 노드를 순서대로 실행한다.

### 4-1. Step 1 — ReqAgent 실행

```
⑲  generic_agent.py:135  node_fn(state) 진입 — "step_1_ReqAgent"

⑳  generic_agent.py:138  _build_user_message() 호출
    └─ generic_agent.py:59-66  ReqAgent + 최초 실행 (ValidationReport 없음)
       → "[PMAgent] 아래 User Story를 분석하여 UseCaseModelArtifact를 작성하라.
          User Story: 로또 번호 생성기"

㉑  generic_agent.py:140  call_llm() 호출 ← 첫 번째 LLM API 콜!
    └─ llm_client.py:157-288  call_llm()
       ├─ llm_client.py:186-188  provider/model 결정 (config 기본값 or step 오버라이드)
       ├─ llm_client.py:189      _PROVIDERS["google"] → _call_google 선택
       │   (멀티 프로바이더: _call_anthropic / _call_google / _call_openai)
       ├─ llm_client.py:198      for attempt in range(1, max_retries + 2): ← 재시도 루프
       │   ├─ _call_google(system, user_message, model, max_tokens)
       │   │   └─ llm_client.py:58-78  Google Gemini API 호출
       │   │       → LLMResponse(text=..., model=..., input_tokens, output_tokens)
       │   ├─ _default_quality_check() → min_response_chars 검증 (기본 500자)
       │   │   ├─ OK → response 반환
       │   │   └─ NG → 재호출 (최대 max_retries=2회)
       │   └─ 429 / RESOURCE_EXHAUSTED 에러 시:
       │       ├─ _is_daily_quota_error() → YES: QuotaExhaustedError 발생
       │       │   → pipeline_status = "quota_exhausted"
       │       │   → partial state 반환 (지금까지 artifacts 저장 가능)
       │       └─ NO (일시적 rate limit):
       │           rate_limit_retries=3회, _extract_retry_delay() 대기 후 재호출

㉒  generic_agent.py:149  extract_yaml_from_response(response.text)
    └─ parser.py:10-43    응답에서 YAML 부분만 추출
       (```yaml 펜스 제거 또는 artifact_id: 시작점 탐색)

㉓  generic_agent.py:165-171  StepResult 생성
    {step_id: "step_1_ReqAgent", agent_id: "ReqAgent",
     artifact_yaml: "artifact_id: UC-01\n...",
     artifact_type: "UseCaseModelArtifact", validation_result: None}

㉔  generic_agent.py:174-175  State 업데이트
    └─ latest_artifacts["UseCaseModelArtifact"] = yaml_str
    └─ steps_completed에 StepResult 추가

㉕  generic_agent.py:187-191  부분 state dict 반환 → LangGraph가 state 병합
```

### 4-2. Step 2 — ValidatorAgent 실행

```
㉖  LangGraph가 엣지 따라 step_2_ValidatorAgent 노드 실행

㉗  generic_agent.py:138  _build_user_message()
    └─ generic_agent.py:73-80  ValidatorAgent 분기
       └─ _find_validation_target(state) → "UseCaseModelArtifact"
       → "아래 UseCaseModelArtifact를 검증하고 ValidationReportArtifact를 작성하라.
          이 artifact 외의 정보는 참조하지 말 것.
          UseCaseModelArtifact:
          artifact_id: UC-01..." ← UC YAML만 전달! (context 격리)

㉘  generic_agent.py:140  call_llm() ← 두 번째 LLM API 콜
    └─ system prompt에는 _ADVERSARIAL_MANDATE가 포함됨
       "List at least 3 potential failure candidates..."
    └─ LLM 응답: ValidationReportArtifact YAML (validation_result: pass|fail)

㉙  generic_agent.py:153-163  ValidatorAgent 전용 처리
    └─ parser.py:53   parse_artifact() → dict로 파싱
    └─ parser.py:87   get_validation_result() → "pass" | "warning" | "fail" 추출

㉚  generic_agent.py:178-179  fail/warning이면 iteration_count += 1

㉛  StepResult 생성 + state 업데이트 후 반환
```

### 4-3. 분기점 — 조건부 라우팅

```
㉜  LangGraph가 conditional edge의 라우팅 함수 실행
    └─ routing.py:19  route_after_validation(state)
       ├─ validation_result == "pass"
       │   → "pass" → step_3_CodeAgent로 진행
       ├─ validation_result == "fail" OR "warning"
       │   └─ iteration_count < max_iterations(3)?
       │       ├─ YES → "rework" → step_1_ReqAgent로 되돌아감 (⑲부터 반복)
       │       └─ NO  → "max_retries" → END (강제 종료)
       │           → pipeline_status = "max_retries_exceeded"
       │
       ★ warning은 fail과 동일하게 rework 처리됨.
         ValidatorAgent가 "warning"을 반환하는 경우:
         - 필수 필드는 있지만 acceptance_criteria가 다소 모호한 경우
         - 스키마 준수는 됐지만 품질 기준에 미흡한 경우
         이 경우도 iteration_count가 증가하고 재작업이 트리거됨.
```

### 4-4. 재작업 시 (rework → ReqAgent 재실행)

```
  ⑲로 되돌아감, 단 _build_user_message()에서:
    └─ generic_agent.py:67-71  ValidationReport가 존재하므로 재작업 모드
       → "[PMAgent] ValidatorAgent가 아래 사유로 이전 artifact를 반려하였다.
          해당 사유만 수정하여 개선된 UseCaseModelArtifact를 재작성하라.
          ValidationReport: (fail 사유 YAML)
          이전 UC Artifact: (이전 UC YAML)
          원본 User Story: 로또 번호 생성기"
```

### 4-5. Step 3 — CodeAgent 실행 (pass 후)

```
㉝  generic_agent.py:82-94  _build_user_message() CodeAgent 분기
    → "아래 승인된 artifacts를 기반으로 ImplementationArtifact를 작성하라.
       UseCaseModelArtifact: (승인된 UC YAML)"

㉞  call_llm() ← LLM API 콜 (max_tokens=16384)
    → ImplementationArtifact YAML 생성 (code_files 포함)

㉟  StepResult 생성 + state 업데이트 → END
```

---

## Phase 5: 결과 저장

**`run_poc.py:164-165` → `_save_artifacts(final_state, output/)`**

```
㊱  run_poc.py:36-50   steps_completed 전체 순회
    └─ parser.py extract_artifact_id() → YAML에서 artifact_id 추출
    └─ parser.py extract_iteration() → iteration 번호 추출
    └─ iteration별 디렉토리에 파일 저장
       output/iteration-01/artifacts/001_UC-01.yaml
       output/iteration-01/artifacts/002_UC-01-VAL-1.yaml
       ...

㊲  run_poc.py:57-81   ImplementationArtifact에서 코드 파일 추출
    └─ code_extractor.py  write_code_files() → workspace/에 실행 가능한 코드 저장
```

---

## 전체 요약 다이어그램

```
run_poc.py:main()
 │
 ├─ config.py                    ← 환경변수/경로 설정
 │
 ├─ graph_builder.py
 │   ├─ load_pipeline_definition()   ← YAML 파이프라인 정의 로드
 │   │   └─ models.py               ← Pydantic 파싱
 │   │
 │   └─ run_pipeline()
 │       ├─ build_graph_from_definition()
 │       │   └─ [각 step마다]
 │       │       ├─ generic_agent.py:create_agent_node()
 │       │       │   ├─ agent_registry.py:get_agent()    ← Agent 설정 로드
 │       │       │   └─ builder.py:build_system_prompt()  ← 프롬프트 조립
 │       │       │       ├─ loader.py:load_agent_prompt()
 │       │       │       ├─ loader.py:load_template()
 │       │       │       └─ loader.py:load_constitution_excerpt()
 │       │       └─ graph.add_node() / add_edge()
 │       │           └─ routing.py:make_validator_router()
 │       │
 │       └─ compiled.invoke(state)   ← 실행 시작!
 │           └─ [각 노드 실행 시]
 │               ├─ generic_agent.py:node_fn()
 │               │   ├─ _build_user_message()    ← Agent별 입력 조립
 │               │   ├─ llm_client.py:call_llm() ← LLM API 호출
 │               │   │   └─ _call_google() / _call_anthropic() / _call_openai()
 │               │   └─ parser.py:extract_yaml_from_response()
 │               └─ routing.py:route_after_validation()
 │                                               ← pass/rework/max_retries 분기
 │
 └─ _save_artifacts()                ← iteration별 산출물 저장
     ├─ parser.py:extract_artifact_id()
     ├─ parser.py:extract_iteration()
     └─ code_extractor.py:write_code_files()
```

---

## Phase 5: full_spiral 파이프라인

`poc_classic.yaml`이 3단계인 반면, `full_spiral.yaml`은 9단계 전체 SDLC를 수행한다.

```
full_spiral.yaml 구조:
  step 1: ReqAgent       (gemini-2.5-pro)   → UseCaseModelArtifact
  step 2: ValidatorAgent (gemini-2.5-pro)   on_fail: ReqAgent
  step 3: TestAgent      (gemini-2.5-flash) mode=design → TestDesignArtifact
  step 4: ValidatorAgent (gemini-2.5-flash) on_fail: TestAgent
  step 5: CodeAgent      (gemini-2.5-pro)   max_tokens=16384 → ImplementationArtifact
  step 6: ValidatorAgent (gemini-2.5-pro)   on_fail: CodeAgent
  step 7: TestAgent      (gemini-2.5-flash) mode=execution → TestReportArtifact
  step 8: ValidatorAgent (gemini-2.5-flash) on_fail: TestAgent
  step 9: CoordAgent     (gemini-2.5-pro)   → FeedbackArtifact
```

### full_spiral에서 poc_classic과 다른 점

**TestAgent (mode=design, step 3)**
- `_build_user_message()` — TestAgent design 분기:
  "아래 UseCaseModelArtifact를 기반으로 TestDesignArtifact를 작성하라."
- ValidatorAgent가 TestDesign을 검증하여 fail 시 TestAgent로 재작업 루프

**CodeAgent (step 5) — full_spiral에서는 TestDesign도 함께 입력**
- `_build_user_message()` — CodeAgent 분기:
  UC artifact + TestDesign artifact 동시 전달
  "아래 승인된 artifacts를 기반으로 ImplementationArtifact를 작성하라."

**TestAgent (mode=execution, step 7)**
- `_resolve_output_type("TestAgent", step)` → mode=execution → "TestReportArtifact"
- `_build_user_message()` — TestAgent execution 분기:
  "아래 artifacts를 기반으로 TestReportArtifact를 작성하라.
   TestDesignArtifact: ... ImplementationArtifact: ..."

**CoordAgent (step 9)**
- `_build_user_message()` — CoordAgent 분기:
  "아래 TestReportArtifact를 기반으로 FeedbackArtifact를 작성하라."
- on_fail 없음 → 단순 엣지 → END

### 산출물 저장 구조 (full_spiral 실행 시)

```
output/
├── iteration-01/artifacts/
│   ├── 001_UC-01.yaml         (ReqAgent)
│   ├── 002_UC-01-VAL-1.yaml   (ValidatorAgent UC 검증)
│   ├── 003_TD-01.yaml         (TestAgent design)
│   ├── 004_TD-01-VAL-1.yaml   (ValidatorAgent TD 검증)
│   ├── 005_IMPL-01.yaml       (CodeAgent)
│   ├── 006_IMPL-01-VAL-1.yaml (ValidatorAgent Impl 검증)
│   ├── 007_TEST-01.yaml       (TestAgent execution)
│   └── 008_TEST-01-VAL-1.yaml (ValidatorAgent TR 검증)
└── workspace/
    └── (실행 가능한 코드 파일)
```

재작업이 발생하면 iteration-02/ 디렉토리에 해당 Phase부터의 artifacts가 저장된다.

---

## 파일별 역할 요약

| 파일 | 역할 |
|------|------|
| `run_poc.py` | 엔트리포인트. CLI 인자 파싱, 파이프라인 실행, 산출물 저장 |
| `src/config.py` | 환경변수 로딩, 경로/모델/프로바이더 설정 |
| `src/pipeline/graph_builder.py` | 파이프라인 YAML → LangGraph 그래프 빌드 및 실행 |
| `src/pipeline/state.py` | `PipelineState`, `StepResult` TypedDict 정의 |
| `src/pipeline/routing.py` | ValidatorAgent 후 조건부 라우팅 함수 생성 |
| `src/executor/generic_agent.py` | 범용 Agent 노드 팩토리. 프롬프트 조립 → LLM 호출 → 결과 파싱 |
| `src/registry/agent_registry.py` | `agent-configs/*.config.yaml`에서 Agent 설정 로드 |
| `src/registry/models.py` | `AgentConfig`, `StepDefinition`, `PipelineDefinition` Pydantic 모델 |
| `src/prompts/builder.py` | Agent별 system prompt 조립 (공통규칙 + Agent프롬프트 + 템플릿 + 헌법) |
| `src/prompts/loader.py` | `open-sdlc-engine/` 디렉토리에서 프롬프트/템플릿/헌법 파일 읽기 |
| `src/llm_client.py` | 멀티 프로바이더 LLM 호출 (Anthropic/Google/OpenAI), 재시도/품질검증 |
| `src/artifacts/parser.py` | LLM 응답에서 YAML 추출, artifact_id/iteration 파싱, validation_result 추출 |
| `src/artifacts/code_extractor.py` | ImplementationArtifact에서 code_files 추출 → 실행 가능 파일 생성 |
| `pipelines/poc_classic.yaml` | 3노드 PoC 파이프라인 정의 (ReqAgent → Validator → CodeAgent) |
| `pipelines/full_spiral.yaml` | 9단계 Full Spiral 파이프라인 정의 |
