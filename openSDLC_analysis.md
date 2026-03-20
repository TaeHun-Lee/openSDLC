# OpenSDLC 구현 전략 분석서

## 1. 기획안 현황 진단

### 잘 잡혀있는 부분
- **Agent 역할 분리가 명확**: RequAgent → LogiAgent → PhysAgent → ConsAgent의 파이프라인이 실제 SDLC 단계와 1:1로 대응
- **Spiral model 적용 의도**: 반복/점진적 개발이라는 핵심 철학이 분명
- **산출물 기반 인터페이스**: Agent 간 소통을 "작업 지시서(프롬프트)" 형태로 표준화하려는 설계
- **Context 유지 전략**: plan-do-see-self feedback 기반의 이력 관리 구상

### 구체화가 필요한 부분
- **Agent 간 산출물 전달 방법**: 3.A항이 비어있음 — 이것이 사실상 시스템의 핵심 메커니즘
- **품질 요구사항(TBD)**: 비기능 요구사항 처리 방식 미정
- **ConsAgent의 역할 범위**: "컴포넌트 단위"로만 기술, 실행/테스트 범위 불명확
- **사용자 인터렉션 포인트**: 어느 시점에 사용자가 개입하는지 미정의
- **반복 종료 조건**: Spiral의 각 iteration이 언제 완료되는지 기준 부재

---

## 2. 핵심 설계 결정 사항 (구현 전 반드시 확정)

### 2.1 Agent 통신 패턴 선택

**Option A: 파일 기반 메시지 패싱 (추천)**
- 각 Agent가 .md 파일로 산출물을 생성, 다음 Agent가 이를 읽어서 작업
- 장점: 디버깅 용이, 사람이 중간에 개입/수정 가능, 이력 자동 보존
- 구현: 프로젝트 디렉토리 내 `/iterations/iter-{n}/{agent_name}/` 구조

**Option B: 이벤트 기반 메시지 큐**
- Agent 간 메시지를 큐(Redis, RabbitMQ 등)로 전달
- 장점: 비동기 처리, 확장성
- 단점: 초기 복잡도 높음, 오버엔지니어링 위험

**Option C: 하이브리드 (중장기 추천)**
- MVP는 파일 기반, 이후 이벤트 기반으로 전환
- 파일은 산출물 영속성용, 이벤트는 Agent 트리거용

### 2.2 LLM 호출 전략

| 항목 | 권장 방식 |
|------|-----------|
| LLM Provider | Anthropic Claude API (주력) + OpenAI GPT 호환 레이어 |
| Agent별 모델 | RequAgent/LogiAgent → Claude Sonnet (비용효율), ConsAgent → Claude Opus (코드 품질) |
| 프롬프트 관리 | 각 Agent별 시스템 프롬프트를 별도 템플릿 파일로 관리 |
| Context 주입 | 이전 iteration 산출물 + 현재 작업지시서를 프롬프트에 포함 |
| Token 관리 | 긴 산출물은 요약본을 만들어 context window 절약 |

### 2.3 상태 관리 모델

```
project/
├── project.json              # 프로젝트 메타 (이름, 생성일, 현재 iteration)
├── config/
│   ├── agents.json           # Agent별 설정 (모델, 프롬프트 템플릿)
│   └── constraints.json      # 기술 스택, 운영환경 제약사항
├── iterations/
│   ├── iter-1/
│   │   ├── goals.md          # 이번 iteration 목표
│   │   ├── req-agent/
│   │   │   ├── plan.md       # 계획
│   │   │   ├── output.md     # 산출물 (사람용 요약)
│   │   │   ├── prompt-to-logi.md  # LogiAgent에게 보낼 작업지시서
│   │   │   └── log.md        # plan-do-see-feedback 이력
│   │   ├── logi-agent/
│   │   ├── phys-agent/
│   │   ├── cons-agent/
│   │   ├── test-agent/
│   │   └── feedback/
│   │       ├── evaluation.md # 자동 평가 결과
│   │       └── user-review.md # 사용자 피드백
│   └── iter-2/
│       └── ...
└── workspace/                # ConsAgent 실제 코드 작업 공간
    └── src/
```

---

## 3. 기술 스택 추천

### 3.1 Backend (Orchestration Engine)

| 구성요소 | 기술 | 선택 이유 |
|----------|------|-----------|
| Runtime | Python 3.11+ | LLM 에코시스템 최강, LangChain/LangGraph 호환 |
| Agent Framework | **LangGraph** | 상태 머신 기반 Agent 오케스트레이션에 최적화 |
| API Server | FastAPI | 비동기 지원, WebSocket (실시간 진행상황), OpenAPI 자동 문서화 |
| State Store | SQLite (MVP) → PostgreSQL | 프로젝트/iteration 메타데이터 관리 |
| File Store | 로컬 FS (MVP) → S3 호환 | 산출물(.md) 저장 |
| Task Queue | 없음 (MVP) → Celery | 장시간 Agent 작업의 비동기 처리 |

**LangGraph를 추천하는 이유:**
- Agent를 "노드", 산출물 전달을 "엣지"로 모델링하면 기획안의 구조와 정확히 매핑
- 조건부 분기 (예: 테스트 실패 → 다시 ConsAgent로) 지원
- 상태 체크포인트로 iteration 중단/재개 가능
- Human-in-the-loop 패턴 내장

### 3.2 Frontend (GUI Dashboard)

| 구성요소 | 기술 | 선택 이유 |
|----------|------|-----------|
| Framework | **Next.js 14+ (App Router)** | SSR/SSG, API Routes, 풍부한 에코시스템 |
| UI Library | shadcn/ui + Tailwind CSS | 커스터마이즈 용이, 깔끔한 기본 UI |
| 상태 관리 | Zustand 또는 React Query | 서버 상태 동기화 |
| 실시간 통신 | WebSocket (Socket.IO) | Agent 작업 진행률 실시간 표시 |
| 다이어그램 | ReactFlow | Agent 파이프라인 시각화, 노드 기반 편집 |
| 에디터 | Monaco Editor | 산출물(.md) 편집, 코드 하이라이팅 |

### 3.3 대안: 빠른 프로토타이핑

MVP를 가장 빠르게 만들고 싶다면:

| 구성요소 | 경량 대안 |
|----------|-----------|
| 전체 | **Streamlit** (Python 단일 스택) |
| 또는 | **Gradio** + FastAPI 조합 |

→ 2~3주 내에 동작하는 프로토타입 가능, 이후 Next.js로 리빌드

---

## 4. MVP 범위 정의 (Phase 1)

### 4.1 MVP에 포함

1. **프로젝트 생성 & 초기 요구사항 입력**
   - 사용자가 개발 요청을 텍스트로 입력
   - 기술 스택/제약사항 선택 UI

2. **RequAgent 단독 동작**
   - 입력을 받아 요구사항 문서 생성
   - 기능 요구사항 → 유스케이스 형태 산출물
   - 사용자 검토/수정 인터페이스

3. **LogiAgent 연동**
   - RequAgent 산출물을 입력으로 논리 설계 수행
   - 워크플로, API 설계 산출물 생성

4. **CoodAgent 기본 오케스트레이션**
   - RequAgent → LogiAgent 순차 실행
   - 각 Agent 작업 시작/종료 상태 표시
   - 산출물 뷰어 (마크다운 렌더링)

5. **1회 iteration 완수**
   - 단일 iteration 내 RequAgent → LogiAgent 파이프라인
   - 산출물 저장 및 조회

### 4.2 MVP에서 제외 (Phase 2+)

- PhysAgent, ConsAgent 구현
- 실제 코드 생성 및 실행
- 테스트 Agent, 피드백 Agent
- 다중 iteration (Spiral 반복)
- 사용자 중간 개입 (Human-in-the-loop)
- 멀티 프로젝트 관리

---

## 5. 구현 로드맵

### Phase 1: Foundation (4~6주)

**Week 1-2: Core Engine**
- [ ] LangGraph 기반 Agent 프레임워크 셋업
- [ ] RequAgent 프롬프트 설계 & 구현
- [ ] 파일 기반 산출물 생성/저장 구조
- [ ] FastAPI 서버 기본 셋업

**Week 3-4: First Pipeline**
- [ ] LogiAgent 프롬프트 설계 & 구현
- [ ] CoodAgent: RequAgent → LogiAgent 오케스트레이션
- [ ] 산출물 전달 메커니즘 구현
- [ ] WebSocket 기반 진행상황 스트리밍

**Week 5-6: GUI MVP**
- [ ] Next.js 프로젝트 셋업
- [ ] 프로젝트 생성 화면
- [ ] Agent 파이프라인 진행 대시보드
- [ ] 산출물 뷰어 (마크다운)
- [ ] 기본 사용자 검토/승인 UI

### Phase 2: Full Pipeline (4~6주)

- PhysAgent, ConsAgent 추가
- 테스트/피드백 Agent 구현
- Human-in-the-loop 패턴 적용
- Spiral iteration 반복 로직

### Phase 3: Production Ready (4~6주)

- 코드 생성 및 실행 환경 (샌드박스)
- 멀티 프로젝트 관리
- 협업 기능 (팀원 초대, 코멘트)
- 산출물 비교 (iteration 간 diff)
- 배포 파이프라인 연동

---

## 6. 구현 시작점: "Hello World" 체크리스트

아래 순서로 시작하면 가장 효율적입니다:

### Step 1: Agent 1개를 독립적으로 동작시키기
```python
# 가장 먼저 만들 것: RequAgent의 LLM 호출 + 산출물 생성
# 이것이 동작하면 전체 시스템의 기반이 마련됨

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph

# RequAgent가 사용자 입력을 받아 요구사항 문서를 생성하는 것
# 이 한 가지가 성공하면 나머지 Agent는 같은 패턴으로 복제
```

### Step 2: 2개 Agent를 체이닝하기
```
RequAgent 산출물 → CoodAgent가 가공 → LogiAgent에 전달
```
- 이 단계에서 "작업 지시서" 포맷이 확정됨
- Agent 간 인터페이스(input/output 스키마)가 정해짐

### Step 3: 파일 시스템에 산출물 영속화
- iteration 디렉토리 구조 생성
- .md 파일로 산출물 저장
- 다음 실행 시 이전 산출물을 context로 로딩

### Step 4: FastAPI로 API 노출
- `/projects` CRUD
- `/projects/{id}/iterations/{n}/run` — iteration 실행
- `/projects/{id}/iterations/{n}/status` — 진행 상태
- WebSocket: 실시간 Agent 작업 로그 스트리밍

### Step 5: GUI 연결
- 위 API에 Next.js 프론트엔드 연결
- 여기서부터 "어플리케이션"으로서 형태를 갖춤

---

## 7. 리스크 & 대응 방안

| 리스크 | 영향도 | 대응 |
|--------|--------|------|
| LLM 산출물 품질 불안정 | 높음 | Agent별 출력 스키마 강제(structured output), 검증 Agent 추가 |
| Context window 초과 | 높음 | 산출물 요약 전략, 관련 부분만 선택적 주입, RAG 활용 |
| Agent 간 산출물 불일치 | 중간 | CoodAgent에서 산출물 간 일관성 검증, 표준 용어집 관리 |
| Spiral 무한 반복 | 중간 | 최대 iteration 횟수 설정, 수렴 조건 정의 |
| 긴 실행 시간 | 중간 | 스트리밍 표시, Agent별 캐시, 병렬 실행 가능한 부분 식별 |
| 사용자 피로도 | 낮음 | 자동 승인 모드, 요약 뷰 제공, 중요 결정만 사용자에게 위임 |

---

## 8. 참고할 유사 프로젝트

- **ChatDev** (GitHub) — 멀티 Agent 소프트웨어 개발 시뮬레이션
- **MetaGPT** — SDLC 역할 기반 LLM Agent 프레임워크  
- **AutoGen (Microsoft)** — 멀티 Agent 대화 프레임워크
- **CrewAI** — 역할 기반 Agent 오케스트레이션

이들과의 차별점: OpenSDLC는 **Spiral model의 반복/점진성**과 **각 단계 산출물의 영속화/추적**에 초점. 기존 프로젝트들은 대부분 한 번의 직선적 파이프라인만 수행.
