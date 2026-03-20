# PoC Implementation Spec

## 실행 방법 (완성 후)

```bash
cd poc
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
python run_poc.py --user-story "간단한 할 일 관리 앱을 만들어줘. 사용자 등록, 할 일 CRUD, 마감일 알림 기능이 필요해."
```

---

## 의존성

```toml
[project]
name = "open-sdlc-poc"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.2",
    "langchain-anthropic>=0.3",
    "pyyaml>=6.0",
    "pydantic>=2.0",
]
```

---

## 구현 파일별 상세

### 1. `src/config.py`
```python
# 환경변수에서 API 키 로딩
# 모델 설정: claude-sonnet-4-20250514 (PoC 기본)
# 경로 설정: 기존 v1 파일들의 상대 경로
```

### 2. `src/prompts/loader.py`
v1 기존 파일에서 텍스트를 읽어오는 유틸리티.
```python
def load_agent_prompt(agent_name: str) -> str:
    """open-sdlc-engine/prompts/agent/{agent_name}.md 파일 내용 반환"""

def load_template(artifact_type: str) -> str:
    """open-sdlc-engine/templates/{artifact_type} 템플릿 내용 반환"""

def load_constitution_excerpt() -> str:
    """open-sdlc-constitution/에서 핵심 원칙만 발췌하여 반환"""
```

### 3. `src/prompts/builder.py`
Agent별 최종 system prompt를 조립하는 빌더.
```python
def build_req_agent_prompt() -> str:
    """
    조립 순서:
    1. constitution 핵심 원칙
    2. req-agent.md 시스템 프롬프트
    3. UseCaseModelArtifact 템플릿 (출력 포맷 참조용)
    """

def build_validator_agent_prompt() -> str:
    """
    조립 순서:
    1. constitution 핵심 원칙 (검증 관련)
    2. validator-agent.md 시스템 프롬프트
    3. 검증 대상 아티팩트 템플릿 (스키마 참조용)
    4. adversarial prompting 지시문 추가
    5. 6가지 감사 기준 체크리스트
    """

def build_code_agent_prompt() -> str:
    """
    조립 순서:
    1. constitution 핵심 원칙
    2. code-agent.md 시스템 프롬프트
    3. ImplementationArtifact 템플릿
    """
```

### 4. `src/nodes/req_agent.py`
```python
async def req_agent_node(state: PipelineState) -> PipelineState:
    """
    독립 LLM 호출로 UC artifact 생성.
    
    첫 실행: user_story를 입력으로 UC 생성
    재작업:  이전 UC + validation fail 사유를 입력으로 개선된 UC 생성
    
    핵심: 이 함수 내에서 생성된 LLM의 응답 중
          YAML artifact 부분만 state에 저장.
          나머지 설명/사고과정은 버린다.
    """
```

### 5. `src/nodes/validator_agent.py`
```python
async def validator_agent_node(state: PipelineState) -> PipelineState:
    """
    독립 LLM 호출로 UC artifact 검증.
    
    입력: state["uc_artifact"] (YAML 문자열) ← 이것만!
    출력: validation_report (YAML) + validation_result (pass/warning/fail)
    
    핵심 금지사항:
    - state에서 user_story를 읽지 않는다 (검증은 artifact 자체만으로)
    - ReqAgent의 system prompt나 응답을 참조하지 않는다
    
    adversarial prompting:
    - "fail 사유 후보 3개를 먼저 나열하라"
    - "blocking 사유가 없을 때만 pass"
    """
```

### 6. `src/graph.py`
```python
def build_poc_graph() -> CompiledGraph:
    """
    LangGraph 파이프라인 구성.
    
    노드: req_agent → validator_agent → (조건부) code_agent | req_agent
    상태: PipelineState TypedDict
    라우팅: validation_result에 따른 pass/rework/max_retries 분기
    """
```

### 7. `run_poc.py`
```python
"""
PoC 실행 엔트리포인트.

사용법:
    python run_poc.py --user-story "..."
    python run_poc.py --user-story "..." --max-iterations 5
    python run_poc.py --test-ambiguous  # 의도적으로 모호한 입력으로 fail 테스트

각 Agent 호출의 입출력을 상세 로깅하여
context 격리가 실제로 동작하는지 확인할 수 있게 한다.
"""
```

---

## 검증 테스트 시나리오

### test_context_isolation.py
```python
"""
context 격리가 실제로 동작하는지 검증:
1. ReqAgent 호출 시 사용된 messages 배열을 캡처
2. ValidatorAgent 호출 시 사용된 messages 배열을 캡처
3. ValidatorAgent의 messages에 ReqAgent의 system prompt가 포함되지 않았는지 확인
4. ValidatorAgent의 messages에 ReqAgent의 assistant 응답이 포함되지 않았는지 확인
"""
```

### test_validation_quality.py
```python
"""
ValidatorAgent가 실제로 결함을 잡아내는지 검증:
1. 의도적으로 필수 필드 누락된 UC → fail 기대
2. acceptance_criteria가 모호한 UC → fail 또는 warning 기대
3. 완전하고 명확한 UC → pass 기대
4. fail 후 재작업한 UC → 품질 향상 확인 (점수 비교)
"""
```

---

## 로깅 전략

모든 LLM 호출을 아래 형식으로 로깅한다:

```
[2024-01-01 12:00:00] [REQ_AGENT] === LLM CALL START ===
[2024-01-01 12:00:00] [REQ_AGENT] System prompt: 1,234 chars (req-agent + constitution + template)
[2024-01-01 12:00:00] [REQ_AGENT] User message: 567 chars (user story)
[2024-01-01 12:00:01] [REQ_AGENT] Response: 2,345 chars
[2024-01-01 12:00:01] [REQ_AGENT] Extracted artifact: 1,890 chars (YAML)
[2024-01-01 12:00:01] [REQ_AGENT] === LLM CALL END ===

[2024-01-01 12:00:02] [VALIDATOR] === LLM CALL START ===
[2024-01-01 12:00:02] [VALIDATOR] System prompt: 987 chars (validator + constitution + checklist)
[2024-01-01 12:00:02] [VALIDATOR] User message: 1,890 chars (UC artifact ONLY ← context 격리 확인)
[2024-01-01 12:00:03] [VALIDATOR] Response: 1,456 chars
[2024-01-01 12:00:03] [VALIDATOR] Validation result: fail
[2024-01-01 12:00:03] [VALIDATOR] Fail reasons: [schema: missing acceptance_criteria, ...]
[2024-01-01 12:00:03] [VALIDATOR] === LLM CALL END ===
```

이 로그를 통해 각 Agent에 실제로 무엇이 전달되었는지 투명하게 확인할 수 있다.
