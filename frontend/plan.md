# OpenSDLC Frontend 구현 계획서

---

## 1. 기술 스택

| 분류 | 선택 | 버전 | 사유 |
|------|------|------|------|
| **프레임워크** | React 19 + Vite 6 | ^19.0, ^6.0 | SSR 불필요 (SPA), 빠른 HMR, 가벼운 번들 |
| **언어** | TypeScript 5.x | ^5.7 | 백엔드 Pydantic 모델과 1:1 타입 매핑 |
| **라우팅** | React Router v7 | ^7.0 | 가장 성숙한 React 라우터, loader/action 패턴 |
| **서버 상태** | TanStack Query v5 | ^5.0 | 캐싱/리페치/뮤테이션, SSE 연동에 유연 |
| **클라이언트 상태** | Zustand | ^5.0 | SSE 이벤트 스트림 실시간 상태 관리, 최소 보일러플레이트 |
| **UI 컴포넌트** | shadcn/ui + Radix UI | latest | 복사-붙여넣기 방식, 완전한 커스터마이징, Tailwind 네이티브 |
| **스타일링** | Tailwind CSS v4 | ^4.0 | shadcn/ui 기본 스타일 시스템, 유틸리티 기반 |
| **SSE 클라이언트** | 커스텀 fetch + ReadableStream | - | EventSource는 헤더 커스터마이징 불가 (API Key 인증 필요) |
| **코드 하이라이팅** | Shiki | ^3.0 | VS Code 동일 엔진, YAML/JS/CSS/HTML 지원 |
| **차트** | Recharts | ^2.0 | React 네이티브, 토큰 사용량 시각화 |
| **아이콘** | Lucide React | latest | shadcn/ui 기본 아이콘셋 |
| **폼 검증** | React Hook Form + Zod | ^7.0, ^3.0 | 파이프라인 에디터 폼 검증 |
| **날짜/시간** | date-fns | ^4.0 | 경량, tree-shakeable |
| **빌드/린트** | ESLint 9 (flat config) + Prettier | ^9.0 | 최신 flat config |

---

## 2. 디렉토리 구조

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── components.json                  ← shadcn/ui 설정
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx                     ← 앱 엔트리
│   ├── App.tsx                      ← 라우터 설정
│   ├── vite-env.d.ts
│   │
│   ├── api/                         ← API 클라이언트 레이어
│   │   ├── client.ts                ← axios 또는 fetch wrapper (baseURL, auth 헤더)
│   │   ├── sse.ts                   ← SSE 커스텀 클라이언트 (재연결, last_event_id 추적)
│   │   ├── types.ts                 ← 백엔드 Pydantic 모델 → TS 인터페이스
│   │   ├── queries/                 ← TanStack Query hooks
│   │   │   ├── projects.ts          ← useProjects, useProject, useProjectUsage
│   │   │   ├── pipelines.ts         ← usePipelines, usePipeline, useValidatePipeline
│   │   │   ├── agents.ts            ← useAgents, useAgent
│   │   │   ├── runs.ts              ← useRuns, useRun, useRunUsage, useRunArtifacts
│   │   │   └── health.ts            ← useHealth
│   │   └── mutations/               ← TanStack Mutation hooks
│   │       ├── projects.ts          ← useCreateProject, useUpdateProject, useDeleteProject
│   │       ├── pipelines.ts         ← useCreatePipeline, useUpdatePipeline, useDeletePipeline
│   │       └── runs.ts              ← useStartRun, useCancelRun, useResumeRun
│   │
│   ├── stores/                      ← Zustand 스토어 (실시간 상태)
│   │   ├── sse-store.ts             ← SSE 이벤트 스트림 상태 (events[], currentStep, currentIteration)
│   │   ├── narrative-store.ts       ← 대화방 메시지 축적 (agent별/iteration별 그룹핑)
│   │   └── settings-store.ts        ← 테마, API Key 설정 등 클라이언트 상태
│   │
│   ├── hooks/                       ← 커스텀 React hooks
│   │   ├── use-sse-stream.ts        ← SSE 연결 관리 (연결/해제/재연결/last_event_id)
│   │   ├── use-run-progress.ts      ← SSE 이벤트 → 진행률 상태 변환
│   │   └── use-theme.ts             ← 다크/라이트 모드
│   │
│   ├── components/                  ← UI 컴포넌트
│   │   ├── ui/                      ← shadcn/ui 기본 컴포넌트 (Button, Card, Dialog, ...)
│   │   ├── layout/
│   │   │   ├── AppShell.tsx          ← 전체 레이아웃 (사이드바 + 헤더 + 메인)
│   │   │   ├── Sidebar.tsx           ← 프로젝트/실행 네비게이션
│   │   │   └── Header.tsx            ← 상단 바 (설정, 헬스 상태)
│   │   ├── pipeline/
│   │   │   ├── PipelineEditor.tsx    ← 파이프라인 Step 배열 편집 (드래그 앤 드롭)
│   │   │   ├── StepCard.tsx          ← 개별 Step 카드 (Agent 선택, model/provider 설정)
│   │   │   ├── AgentPicker.tsx       ← Agent 선택 드롭다운 (role, inputs/outputs 표시)
│   │   │   ├── PipelineFlowView.tsx  ← artifact_flow 시각화 (노드 그래프)
│   │   │   └── ValidationBanner.tsx  ← 파이프라인 검증 결과 (errors/warnings 표시)
│   │   ├── run/
│   │   │   ├── RunStarter.tsx        ← User Story 입력 + 파이프라인 선택 + 실행 옵션 + 시작
│   │   │   ├── RunProgress.tsx       ← 실시간 진행률 표시 (Iteration/Step 위치)
│   │   │   ├── ProgressTimeline.tsx  ← Step별 타임라인 (시작/완료 시각, verdict 뱃지, 캐시 적중률)
│   │   │   ├── IterationTabs.tsx     ← Iteration 탭 전환 (satisfaction_score 표시)
│   │   │   └── CancelButton.tsx      ← 중단 버튼 (확인 다이얼로그 포함)
│   │   ├── narrative/
│   │   │   ├── NarrativePanel.tsx    ← 대화방 컨테이너 (Agent별 아바타, 타임스탬프)
│   │   │   ├── MessageBubble.tsx     ← 개별 메시지 (agent 이름, rework_seq 뱃지)
│   │   │   ├── ReworkMarker.tsx      ← REWORK_TRIGGERED 이벤트 시각적 구분선
│   │   │   └── StepTransition.tsx    ← Step 전환 구분 표시 (STEP_STARTED/COMPLETED)
│   │   ├── artifacts/
│   │   │   ├── ArtifactViewer.tsx    ← YAML 아티팩트 뷰어 (Shiki 하이라이팅)
│   │   │   ├── CodeViewer.tsx        ← 코드 파일 뷰어 (language별 하이라이팅)
│   │   │   ├── ArtifactList.tsx      ← Iteration별 아티팩트 목록
│   │   │   └── CodeFileTree.tsx      ← 코드 파일 트리 구조
│   │   ├── usage/
│   │   │   ├── TokenUsageChart.tsx   ← 모델별/Agent별 토큰 사용량 차트
│   │   │   └── UsageSummary.tsx      ← 토큰 합계 카드
│   │   └── project/
│   │       ├── ProjectSelector.tsx   ← 프로젝트 생성/선택
│   │       ├── ProjectSettings.tsx   ← 프로젝트 이름/설명 수정
│   │       └── RunHistoryList.tsx    ← 프로젝트 내 Run 이력 목록
│   │
│   ├── pages/                       ← 라우트별 페이지 컴포넌트
│   │   ├── DashboardPage.tsx        ← 메인 대시보드 (프로젝트 목록, 최근 Run)
│   │   ├── PipelinePage.tsx         ← 파이프라인 목록/편집/생성
│   │   ├── RunPage.tsx              ← 실행 중/완료 Run 상세 (진행률 + 대화방 + 산출물)
│   │   ├── ArtifactsPage.tsx        ← 최종 산출물 전체 조회
│   │   ├── UsagePage.tsx            ← 토큰 사용량 대시보드
│   │   └── SettingsPage.tsx         ← API Key, 테마 등 설정
│   │
│   ├── lib/                         ← 유틸리티
│   │   ├── utils.ts                 ← cn() 헬퍼, 공통 유틸
│   │   ├── format.ts               ← 날짜/숫자 포맷팅
│   │   └── constants.ts            ← Agent 아이콘/색상 매핑 등
│   │
│   └── styles/
│       └── globals.css              ← Tailwind 디렉티브 + 커스텀 변수
```

---

## 3. 페이지 구성 및 라우트 설계

```
/                           → DashboardPage      프로젝트 목록 + 최근 Run + 시스템 상태
/pipelines                  → PipelinePage        파이프라인 목록/생성
/pipelines/:name            → PipelinePage        파이프라인 상세/편집
/pipelines/:name/validate   → PipelinePage        검증 결과 (탭)
/runs/new                   → RunPage             새 실행 시작 (User Story 입력)
/runs/:runId                → RunPage             실행 상세 (진행률 + 대화방 + 산출물)
/runs/:runId/artifacts      → ArtifactsPage       최종 산출물 조회
/runs/:runId/usage          → UsagePage           Run 단위 토큰 사용량
/projects/:projectId        → DashboardPage       프로젝트 상세 (소속 Run 이력)
/projects/:projectId/usage  → UsagePage           프로젝트 단위 토큰 사용량
/settings                   → SettingsPage        설정 (API Key, 테마)
```

---

## 4. 핵심 기능 상세 설계

### 4.1 파이프라인 편집기 (요구사항 1)

**화면 구성:**
- 좌측: Agent 팔레트 (사용 가능한 Agent 목록, `GET /api/agents` 로드)
  - 각 Agent 카드에 role, primary_inputs, primary_outputs 표시
- 우측: Step 배열 편집 영역
  - 드래그 앤 드롭으로 Step 순서 변경
  - 각 Step 카드에서 Agent 선택, model, provider, mode(TestAgent 한정), max_tokens 설정
  - ValidatorAgent 추가 시 on_fail 대상 자동 추론 (서버 측 compile_pipeline이 처리)
- 상단: 파이프라인 메타데이터 (name, description, max_iterations, max_reworks_per_gate)
- 하단: 검증 버튼 → `POST /api/pipelines/{name}/validate` 호출
  - errors는 빨간색 배너, warnings는 노란색 배너
  - artifact_flow를 노드-엣지 다이어그램으로 시각화 (Step 간 artifact 흐름)

**기본 파이프라인 보호 정책:**
- `PipelineInfo.is_default=true`인 파이프라인(`full_spiral`)은 수정/삭제가 서버에서 403으로 차단됨
- UI에서 사전 차단: 편집/삭제 버튼 비활성화 + "기본 파이프라인은 수정할 수 없습니다" 툴팁
- "복제(Clone)" 버튼을 제공하여 기본 파이프라인을 복사 후 편집 유도

**파이프라인 생성 시 이름 중복 처리:**
- `POST /api/pipelines`가 409 응답을 반환하면 "이미 존재하는 파이프라인 이름입니다" 에러 표시
- 이름 입력 필드에 `pattern: ^[a-zA-Z0-9][a-zA-Z0-9_-]*$` 클라이언트 검증 적용 (max 64자)

**API 호출 흐름:**
```
GET /api/agents                          → Agent 팔레트 로드
GET /api/pipelines                       → 기존 파이프라인 목록
GET /api/pipelines/{name}                → 파이프라인 상세 (편집 시)
POST /api/pipelines/{name}/validate      → 실행 전 검증
POST /api/pipelines                      → 새 파이프라인 생성 (409: 이름 중복)
PUT /api/pipelines/{name}                → 파이프라인 수정 (403: 기본 파이프라인)
DELETE /api/pipelines/{name}             → 파이프라인 삭제 (403: 기본 파이프라인)
```

**드래그 앤 드롭:** `@dnd-kit/core` + `@dnd-kit/sortable` 사용 (React DnD 대비 경량, 접근성 우수)

### 4.2 실시간 진행률 (요구사항 2)

**SSE 연결 관리 (`use-sse-stream.ts`):**

```typescript
// fetch 기반 SSE 클라이언트 (API Key 헤더 지원)
async function connectEvents(runId: string, lastEventId: number) {
  const url = `/api/runs/${runId}/events?last_event_id=${lastEventId}`;
  const response = await fetch(url, {
    headers: {
      'Accept': 'text/event-stream',
      'X-API-Key': apiKey,  // EventSource에서는 불가능
    },
  });

  const contentType = response.headers.get('Content-Type') || '';

  if (contentType.includes('text/event-stream')) {
    // 활성 Run → SSE 스트림 파싱
    return parseSSEStream(response.body);
  } else {
    // 완료 Run → JSON 배열 (list[EventInfo]) 일괄 로드
    const events: EventInfo[] = await response.json();
    return loadEventsFromReplay(events);
  }
}
```

**응답 형식 분기 처리:**

백엔드 `GET /api/runs/{id}/events`는 Run 상태에 따라 다른 응답을 반환한다:

| Run 상태 | Content-Type | 응답 형식 | 처리 방식 |
|----------|-------------|-----------|-----------|
| 활성 (`running`) | `text/event-stream` | SSE 스트림 | ReadableStream 파싱, 실시간 이벤트 처리 |
| 완료 (`completed`/`failed`/`cancelled`) | `application/json` | `list[EventInfo]` | JSON 일괄 로드 → narrative-store에 적재 |

- 완료 Run의 JSON 리플레이 시 `iteration_num`, `agent_name` 쿼리 파라미터로 필터링 가능
  ```
  GET /api/runs/{id}/events?iteration_num=1&agent_name=ReqAgent
  ```
- `use-sse-stream.ts`에서 `Content-Type` 헤더를 확인하여 스트림/JSON 자동 분기

**재연결 전략:**
1. 연결 끊김 감지 시 3초 후 자동 재연결
2. `last_event_id`를 Zustand 스토어에 저장하여 재연결 시 이어받기
3. 최대 재연결 시도: 10회 (이후 수동 재연결 버튼 표시)
4. 백그라운드 탭 전환 시 `visibilitychange` 이벤트 감지 → 복귀 시 재연결

**진행률 표시 (`RunProgress.tsx`):**
- 상단 프로그레스 바: `Iteration {N} / {max_iterations}` — `Step {M} / {steps_total}`
- 현재 실행 중인 Agent 이름 + 애니메이션 (spinning indicator)
- 경과 시간 실시간 표시
- SSE `STEP_STARTED` / `STEP_COMPLETED` 이벤트로 상태 갱신
- `PIPELINE_STARTED.is_resume=true`이면 프로그레스 바 상단에 "이전 실행에서 이어서 시작합니다" 안내 배너 표시

**타임라인 (`ProgressTimeline.tsx`):**
- 세로 타임라인으로 각 Step을 순차 표시
- 완료 Step: verdict에 따라 pass(초록)/fail(빨강)/warning(노랑) 뱃지
- 현재 Step: pulse 애니메이션
- 대기 Step: 회색 비활성
- Step 완료 뱃지에 캐시 적중률 간단 표시 (cache_read_tokens 비율)
- Step 클릭 시 팝오버: model_used, provider, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens 상세 표시

### 4.3 실시간 산출물 조회 (요구사항 3)

**동작 방식:**
1. SSE `STEP_COMPLETED` 이벤트 수신 시 `output_artifact` 필드 확인
2. `GET /api/runs/{runId}/iterations/{iterNum}/artifacts` 호출하여 해당 Iteration의 최신 산출물 로드
3. Shiki로 YAML 구문 강조 적용하여 렌더링
4. Iteration 전환 시 탭으로 이전 Iteration 산출물도 비교 조회 가능

**ArtifactViewer 구성:**
- 상단: artifact_type 탭 (UseCaseModelArtifact, ValidationReportArtifact, ImplementationArtifact, ...)
- 본문: YAML 콘텐츠 (Shiki 하이라이팅, line number)
- 우측: artifact 메타정보 (artifact_id, 생성 시각)
- 접기/펼치기 지원 (긴 artifact 대응)

### 4.4 Agent Narrative 대화방 (요구사항 4)

**대화방 구조 (`NarrativePanel.tsx`):**
```
┌──────────────────────────────────────────────┐
│  ℹ️ 이전 실행에서 이어서 시작합니다 (Resume)  │  ← is_resume=true 시
│ ─────────────────────────────────────────── │
│  Iteration 1                                 │
│  [필터: Agent ▾] [Iteration ▾]               │  ← 완료 Run에서만 표시
│ ─────────────────────────────────────────── │
│  ▶ Step 1: PMAgent                          │
│  ┌──────────────────────────────────┐       │
│  │ 🤖 PMAgent                       │       │
│  │ 프로젝트를 초기화합니다...         │       │
│  │ 12:03:45                          │       │
│  └──────────────────────────────────┘       │
│                                              │
│  ▶ Step 2: ReqAgent                         │
│  ┌──────────────────────────────────┐       │
│  │ 📋 ReqAgent                      │       │
│  │ 요구사항을 분석합니다...           │       │
│  │ 12:04:12                          │       │
│  └──────────────────────────────────┘       │
│                                              │
│  ▶ Step 3: ValidatorAgent                   │
│  ┌──────────────────────────────────┐       │
│  │ ✅ ValidatorAgent                 │       │
│  │ 검증 결과: FAIL                   │       │
│  │ 12:05:30                          │       │
│  └──────────────────────────────────┘       │
│                                              │
│  ⚡ REWORK TRIGGERED → ReqAgent (rework #1) │
│  ─────────────────────────────────────────── │
│  ▶ Step 2: ReqAgent (rework #1)             │
│  ┌──────────────────────────────────┐       │
│  │ 📋 ReqAgent                      │       │
│  │ 검증 피드백을 반영하여 재작업...    │       │
│  │ 12:05:32                          │       │
│  └──────────────────────────────────┘       │
└──────────────────────────────────────────────┘
```

**이벤트 → 메시지 변환 규칙:**

| SSE 이벤트 | 대화방 표시 |
|------------|------------|
| `pipeline_started` | 시작 배너. `is_resume=true`이면 "이전 실행에서 이어서 시작" 안내 추가 |
| `step_started` | Step 전환 헤더 (agent 이름, input_artifacts, expected_output) |
| `agent_narrative` | 메시지 버블 (agent 아바타, 텍스트, 타임스탬프, rework_seq 뱃지) |
| `step_completed` | Step 완료 뱃지 (verdict, model_used, 토큰 수, cache 적중률) |
| `validation_result` | 검증 결과 카드 (pass/fail/warning, rework_seq) |
| `rework_triggered` | 구분선 + 라벨 (rework_target, rework_seq, validation_result) |
| `pipeline_completed` | 완료 배너 (iterations_completed, steps_completed) |
| `pipeline_error` | 에러 배너. `type=cancelled`: "사용자 요청으로 중단됨", `type=quota_exhausted`: "LLM API 할당량 초과", 기타: error 메시지 표시 |

**완료 Run 이벤트 필터링 (DB 리플레이):**

완료된 Run의 대화방에서는 백엔드 DB 리플레이 API의 필터링 기능을 활용:
- Agent 필터 드롭다운: 특정 Agent의 narrative만 표시 (`?agent_name=ReqAgent`)
- Iteration 필터 드롭다운: 특정 Iteration의 이벤트만 표시 (`?iteration_num=2`)
- 필터 적용 시 `GET /api/runs/{id}/events?iteration_num=N&agent_name=X`로 재요청

**Narrative 스토어 구조:**
```typescript
interface NarrativeStore {
  messages: NarrativeMessage[];      // 전체 메시지 시계열
  byIteration: Map<number, NarrativeMessage[]>;  // Iteration별 그룹
  isResume: boolean;                 // Resume된 실행인지 여부
  addEvent: (event: SSEEvent) => void;
  loadFromReplay: (events: EventInfo[]) => void;  // JSON 리플레이 일괄 로드
  clear: () => void;
}
```

**자동 스크롤:** 새 메시지 수신 시 하단으로 자동 스크롤, 사용자가 위로 스크롤 시 자동 스크롤 일시 중지 (스크롤 위치 감지)

### 4.5 중단 및 재실행 기능 (요구사항 5)

**CancelButton 동작:**
1. 버튼 클릭 → 확인 다이얼로그: "현재 진행 중인 Step이 완료된 후 파이프라인이 중단됩니다. 계속하시겠습니까?"
2. 확인 시 `POST /api/runs/{runId}/cancel` 호출 (202 응답)
3. 버튼 상태 → "중단 요청됨..." (disabled, spinner 표시)
4. SSE `PIPELINE_ERROR` 이벤트 (`type=cancelled`)로 최종 중단 확인
5. 중단 후 "재실행(Resume)" 버튼 표시 → `POST /api/runs/{runId}/resume`

**에러 응답 처리:**

| API | 에러 코드 | 의미 | UI 처리 |
|-----|-----------|------|---------|
| `POST /cancel` | 409 | Run이 이미 활성 상태가 아님 | "이미 완료/중단된 실행입니다" 토스트, 상태 새로고침 |
| `POST /cancel` | 404 | Run 미존재 | "실행을 찾을 수 없습니다" 에러 |
| `POST /resume` | 409 | Run이 running 또는 completed 상태 | "재실행할 수 없는 상태입니다" 토스트 |
| `POST /resume` | 404 | Run 미존재 | "실행을 찾을 수 없습니다" 에러 |

**상태별 버튼 표시:**

| Run 상태 | 표시 버튼 |
|----------|----------|
| `running` | Cancel |
| `cancelling` (cancel 요청 후 ~ 실제 중단 전) | "중단 중..." (disabled) |
| `cancelled` | Resume |
| `failed` | Resume |
| `completed` | (없음) |

### 4.6 최종 산출물 조회 (요구사항 6)

**ArtifactsPage 구성:**
- 좌측 사이드바: Iteration 선택 (마지막 Iteration 기본 선택)
- 메인 영역 상단 탭:
  - **Artifacts**: YAML 아티팩트 목록 (artifact_type별 탭)
  - **Code Files**: 코드 파일 트리 + 뷰어
- 각 아티팩트/코드 파일에 복사 버튼 (클립보드 복사)
- 코드 파일 전체 다운로드 버튼 (향후 백엔드 zip 엔드포인트 필요 가능)

**API 호출:**
```
GET /api/runs/{runId}/artifacts                          → 전체 산출물
GET /api/runs/{runId}/iterations/{num}/artifacts          → Iteration별 산출물
```

---

## 5. 추가 보완 기능

### 5.1 프로젝트 관리

| 기능 | API | 컴포넌트 |
|------|-----|----------|
| 프로젝트 생성 | `POST /api/projects` | ProjectSelector |
| 프로젝트 목록 | `GET /api/projects` | Sidebar / DashboardPage |
| 프로젝트 상세 (Run 이력) | `GET /api/projects/{id}` | DashboardPage |
| 프로젝트 수정 | `PUT /api/projects/{id}` | ProjectSettings |
| 프로젝트 삭제 | `DELETE /api/projects/{id}` | ProjectSettings |

### 5.2 Run 시작 옵션 (RunStarter 상세)

**기본 입력:**
- **User Story** 텍스트 영역 (최소 10자)
- **파이프라인 선택** 드롭다운 (`GET /api/pipelines` 로드)
- **프로젝트 연결** 드롭다운 (선택, `GET /api/projects` 로드)

**고급 설정 (접기/펼치기):**
- **max_iterations** 슬라이더/숫자 입력 (1~10, 기본값: 선택된 파이프라인의 max_iterations)
- **Webhook URL** 입력 필드 (선택)
- **Webhook Events** 체크박스: `completed` / `failed` / `cancelled` (webhook_url 입력 시 활성화)

**실행 전 자동 검증:**
- "실행" 버튼 클릭 → `POST /api/pipelines/{name}/validate` 자동 호출
- errors → 실행 차단, 에러 목록 표시
- warnings → 경고 표시 + "이 경고를 무시하고 실행하시겠습니까?" 확인
- valid → 즉시 `POST /api/runs` 호출

**동시 실행 제한:**
- 백엔드 `RunManager`는 최대 2개 동시 실행 (`max_concurrent=2`)
- 503 또는 429 응답 시 "현재 최대 실행 수에 도달했습니다. 잠시 후 다시 시도해주세요." 안내

### 5.3 Run 이력 및 재실행

- DashboardPage에 최근 Run 목록 (status 뱃지, 파이프라인 이름, 생성 시각)
- `GET /api/runs?project_id=xxx`로 프로젝트별 필터링 조회
- 실패/취소된 Run에 Resume 버튼
- Run 상세 → 동일 파이프라인 + user_story로 새 Run 시작 (복제)

### 5.4 SSE 재연결 처리

```
연결 상태 UI:
┌─────────────────────────────────────────┐
│ 🟢 Connected                            │  ← 정상 연결
│ 🟡 Reconnecting... (attempt 2/10)       │  ← 재연결 중
│ 🔴 Disconnected — [Reconnect] 버튼      │  ← 재연결 실패
└─────────────────────────────────────────┘
```

### 5.5 파이프라인 실행 전 검증

- Run 시작 버튼 클릭 시 자동으로 `POST /api/pipelines/{name}/validate` 호출
- errors가 있으면 실행 차단 + 에러 표시
- warnings만 있으면 경고 표시 후 사용자 확인으로 실행 진행 가능
- artifact_flow를 간단한 화살표 다이어그램으로 시각화

### 5.6 토큰 사용량 대시보드

**Run Usage 화면 (`/runs/:runId/usage`):**
- 총 토큰 수 카드 (input / output / cache_read / cache_creation)
- 모델별 파이 차트 (by_model)
- Agent별 막대 차트 (by_agent)
- Iteration별 추이 라인 차트 (by_iteration)

**Project Usage 화면 (`/projects/:projectId/usage`):**
- 프로젝트 누적 토큰 수
- 파이프라인별 사용량 비교 (by_pipeline)
- 모델별 비용 분석 (by_model)

### 5.7 헬스 체크 및 시스템 상태

- Header에 백엔드 연결 상태 표시 (`GET /api/health` 주기적 폴링)
- 현재 LLM provider/model 표시
- 연결 실패 시 "서버 연결 불가" 배너

### 5.8 다크 모드

- shadcn/ui 기본 다크 모드 지원 활용
- 시스템 설정 자동 감지 + 수동 토글
- `settings-store.ts`에 테마 설정 저장 (localStorage)

### 5.9 API Key 설정 UI

- 백엔드에 `OPENSDLC_API_KEY`가 설정된 경우 프론트엔드에서 API Key 입력 필요
- SettingsPage에서 API Key 입력 → localStorage에 저장
- 모든 API 요청의 `X-API-Key` 헤더에 자동 첨부
- 인증 실패(401) 시 자동으로 API Key 입력 다이얼로그 표시

### 5.10 Iteration 만족도 점수 표시

- `IterationInfo.satisfaction_score` 필드: PMAgent가 평가한 Iteration 만족도 (0~100)
- `IterationTabs.tsx`에서 각 Iteration 탭에 만족도 점수 뱃지 표시 (예: "⭐ 72")
- 완료된 Iteration만 점수 표시, 진행 중인 Iteration은 "진행중" 표시
- Iteration 간 만족도 추이를 시각적으로 비교 가능

### 5.11 HTTP 에러 핸들링 전략

모든 API 뮤테이션에 대해 백엔드 에러 응답을 일관된 UX로 처리한다:

| HTTP 상태 | 의미 | 프론트엔드 처리 |
|-----------|------|----------------|
| 401 | API Key 인증 실패 | API Key 입력 다이얼로그 자동 표시 |
| 403 | 기본 파이프라인 수정/삭제 시도 | "기본 파이프라인은 수정/삭제할 수 없습니다" 토스트 |
| 404 | 리소스 미존재 | 목록 페이지로 리다이렉트 + "리소스를 찾을 수 없습니다" 토스트 |
| 409 | 상태 충돌 (파이프라인 이름 중복, Run 상태 부적합) | 상황별 메시지 토스트 |
| 422 | 파이프라인 검증 실패 | 에러 목록 인라인 표시 |
| 500+ | 서버 내부 오류 | "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요." 토스트 |

**글로벌 에러 인터셉터:**
- `api/client.ts`의 fetch wrapper에서 응답 상태 코드를 일괄 처리
- 401 → `settings-store`의 `showApiKeyDialog()` 호출
- 네트워크 에러 → "서버에 연결할 수 없습니다" 배너 + 자동 재시도 (3회)

### 5.12 TypeScript 타입 정의 정책

`api/types.ts`에서 백엔드 Pydantic 모델을 1:1 매핑:

- `RunDetail` 타입: 레거시 필드 (`steps: StepResultInfo[]`, `artifacts: Record<string, string>`)를 optional로 포함하되, UI에서는 `iterations: IterationInfo[]` 트리만 사용
- 모든 timestamp 필드는 `number` (Unix epoch seconds), 표시 시 `date-fns`로 포맷
- nullable 필드는 `| null`로 명시, API 응답의 빈 배열은 `[]` 기본값

---

## 6. SSE 이벤트 타입별 프론트엔드 처리 매핑

| SSE event_type | Zustand 액션 | UI 반응 |
|----------------|-------------|---------|
| `pipeline_started` | setStatus("running"), setStepsTotal | 프로그레스 바 초기화 |
| `step_started` | setCurrentStep, setCurrentAgent, addNarrative | 타임라인 현재 Step 활성화, 대화방 헤더 추가 |
| `agent_narrative` | addNarrative | 대화방 메시지 버블 추가, 자동 스크롤 |
| `step_completed` | updateStep(verdict, tokens), addNarrative | 타임라인 뱃지 업데이트, TanStack Query invalidate(artifacts) |
| `validation_result` | addNarrative | 검증 결과 카드 표시 |
| `rework_triggered` | incrementReworkSeq, addNarrative | 대화방 구분선, 타임라인 rework 표시 |
| `pipeline_completed` | setStatus("completed") | 프로그레스 바 완료, 산출물 자동 로드 |
| `pipeline_error` | setStatus("failed"), setError | 에러 배너 표시 |
| `log` | addLog | (디버그 콘솔에만 표시, 기본 숨김) |

---

## 7. 백엔드 API 전체 매핑

| API | 메서드 | 프론트엔드 사용처 |
|-----|--------|------------------|
| `/api/health` | GET | Header 상태 표시 |
| `/api/agents` | GET | PipelineEditor AgentPicker |
| `/api/agents/{id}` | GET | Agent 상세 툴팁 |
| `/api/pipelines` | GET | PipelinePage 목록, RunStarter 선택 |
| `/api/pipelines/{name}` | GET | PipelinePage 상세/편집 |
| `/api/pipelines/{name}/validate` | POST | 실행 전 검증, PipelineEditor 검증 |
| `/api/pipelines` | POST | PipelineEditor 생성 |
| `/api/pipelines/{name}` | PUT | PipelineEditor 수정 |
| `/api/pipelines/{name}` | DELETE | PipelinePage 삭제 |
| `/api/projects` | GET | Sidebar 프로젝트 목록 |
| `/api/projects` | POST | ProjectSelector 생성 |
| `/api/projects/{id}` | GET | DashboardPage 프로젝트 상세 |
| `/api/projects/{id}` | PUT | ProjectSettings 수정 |
| `/api/projects/{id}` | DELETE | ProjectSettings 삭제 |
| `/api/projects/{id}/usage` | GET | UsagePage 프로젝트 사용량 |
| `/api/runs` | GET | DashboardPage 실행 목록 |
| `/api/runs` | POST | RunStarter 실행 시작 |
| `/api/runs/{id}` | GET | RunPage 상세 |
| `/api/runs/{id}/events` | GET (SSE) | RunPage 실시간 스트림 |
| `/api/runs/{id}/artifacts` | GET | ArtifactsPage 산출물 |
| `/api/runs/{id}/iterations/{n}` | GET | RunPage Iteration 상세 |
| `/api/runs/{id}/iterations/{n}/steps` | GET | RunPage Step 목록 |
| `/api/runs/{id}/iterations/{n}/artifacts` | GET | RunPage Iteration 산출물 |
| `/api/runs/{id}/progress` | GET | RunPage 폴링 폴백 (SSE 불가 시) |
| `/api/runs/{id}/usage` | GET | UsagePage Run 사용량 |
| `/api/runs/{id}/cancel` | POST | CancelButton |
| `/api/runs/{id}/resume` | POST | Resume 버튼 |

---

## 8. 구현 순서

### Phase 1: 프로젝트 초기화 및 기반 구축
1. Vite + React + TypeScript 프로젝트 생성
2. Tailwind CSS v4 + shadcn/ui 설정
3. React Router v7 라우트 설정
4. API 클라이언트 + TanStack Query 설정
5. 기본 레이아웃 (AppShell, Sidebar, Header)
6. 다크 모드 구현

### Phase 2: 파이프라인 관리
7. Agent 목록 조회 UI
8. 파이프라인 목록/상세 조회 UI
9. 파이프라인 에디터 (Step 배열 편집, 드래그 앤 드롭)
10. 파이프라인 검증 UI

### Phase 3: 실행 및 실시간 모니터링
11. 프로젝트 관리 (CRUD)
12. Run 시작 화면 (User Story 입력, 파이프라인 선택, 프로젝트 연결)
13. SSE 커스텀 클라이언트 (재연결, last_event_id 추적)
14. 실시간 진행률 표시 (프로그레스 바, 타임라인)
15. Agent Narrative 대화방
16. 중단/재실행 기능

### Phase 4: 산출물 및 분석
17. 산출물 뷰어 (YAML + 코드, Shiki 하이라이팅)
18. 최종 산출물 페이지 (코드 파일 트리)
19. 토큰 사용량 대시보드 (차트)
20. Run 이력 및 프로젝트 대시보드

### Phase 5: 마무리
21. API Key 인증 UI
22. 에러 핸들링 전역화 (401 → API Key 다이얼로그, 네트워크 에러 → 재시도)
23. 반응형 레이아웃 (모바일 최소 지원)
24. 빌드 최적화 (코드 스플리팅, lazy loading)
