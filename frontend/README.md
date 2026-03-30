# OpenSDLC Frontend

AI Software Factory의 웹 인터페이스. 파이프라인 관리, 실행 모니터링, 산출물 조회, 토큰 사용량 분석 기능을 제공한다.

---

## 기술 스택

| 분류 | 기술 | 버전 |
|------|------|------|
| 프레임워크 | React + Vite | 19 / 8 |
| 언어 | TypeScript | 5.9 |
| 라우팅 | React Router | v7 |
| 서버 상태 | TanStack Query | v5 |
| 클라이언트 상태 | Zustand | v5 |
| UI | shadcn/ui + Radix UI + Tailwind CSS v4 | - |
| 코드 하이라이팅 | Shiki | v4 |
| 차트 | Recharts | v3 |

---

## 1. 사전 준비

### 1-1. Python 가상환경

Backend 실행을 위해 프로젝트 전용 가상환경이 필요하다.

```bash
# 가상환경이 없다면 생성
python3 -m venv ~/opensdlc-venv

# 활성화 (모든 터미널에서 필수)
source ~/opensdlc-venv/bin/activate
```

### 1-2. Backend 의존성 설치

```bash
cd backend
pip install -e ".[all-llm]"    # 전체 LLM 프로바이더 (anthropic, google, openai)
# 또는 특정 프로바이더만:
# pip install -e ".[anthropic]"
# pip install -e ".[google]"
```

### 1-3. Frontend 의존성 설치

```bash
cd frontend
npm install
```

### 1-4. LLM API 키 설정

실제 파이프라인 실행(Run)을 하려면 LLM API 키가 필요하다. Backend 디렉토리에 `.env` 파일을 생성한다.

```bash
# backend/.env
OPENSDLC_LLM_PROVIDER=google          # google / anthropic / openai
GOOGLE_API_KEY=your-key-here           # 선택한 프로바이더에 맞는 키
# ANTHROPIC_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here
```

> LLM 키 없이도 프로젝트 관리, 파이프라인 편집, UI 탐색 등 대부분의 기능을 확인할 수 있다.
> 실제 Run 실행만 LLM 키가 필요하다.

---

## 2. 실행 방법

**터미널 2개**를 열어 Backend와 Frontend를 각각 실행한다.

### 터미널 1: Backend (FastAPI, 포트 8000)

```bash
source ~/opensdlc-venv/bin/activate
cd backend
python run_server.py --reload
```

정상 실행 시 출력:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO  [alembic.runtime.migration] Running upgrade  -> 5a9668ff4ada, initial schema
INFO  [alembic.runtime.migration] Running upgrade ... -> ..., add indexes on FK columns
INFO  [alembic.runtime.migration] Running upgrade ... -> ..., add webhook columns to runs
INFO:     Application startup complete.
```

### 터미널 2: Frontend (Vite dev server, 포트 5173)

```bash
cd frontend
npm run dev
```

정상 실행 시 출력:
```
VITE v8.x.x  ready in XXXms
  ➜  Local:   http://localhost:5173/
```

### 브라우저에서 접속

```
http://localhost:5173
```

> Vite가 `/api/*` 요청을 `http://localhost:8000`으로 프록시하므로, 프론트엔드에서 별도 설정 없이 백엔드 API를 호출한다.

---

## 3. 기능별 확인 가이드

### 3-1. 대시보드 (Dashboard)

**경로:** `/` (메인 페이지)

| 확인 항목 | 방법 |
|-----------|------|
| 프로젝트 생성 | 우측 상단 "New Project" 버튼 클릭 → 이름/설명 입력 → 생성 |
| 프로젝트 목록 | 생성된 프로젝트가 카드로 표시되는지 확인 |
| 최근 Run 목록 | Run 실행 후 최신순으로 표시되는지 확인 |
| 프로젝트 필터링 | 사이드바에서 프로젝트 클릭 → 해당 프로젝트의 Run만 필터 |

### 3-2. 프로젝트 관리

**경로:** `/projects/:projectId/settings`

| 확인 항목 | 방법 |
|-----------|------|
| 프로젝트 수정 | 대시보드에서 프로젝트 클릭 → Settings → 이름/설명 변경 → 저장 |
| 프로젝트 삭제 | Settings 페이지 하단 Danger Zone → "Delete" 클릭 → 확인 다이얼로그 |
| 사이드바 반영 | 생성/삭제 후 좌측 사이드바 프로젝트 목록이 실시간 갱신되는지 확인 |

### 3-3. 파이프라인 관리

**경로:** `/pipelines`

| 확인 항목 | 방법 |
|-----------|------|
| 파이프라인 목록 | 기본 파이프라인 `full_spiral`이 표시되는지 확인 |
| 파이프라인 상세 | 파이프라인 클릭 → 12개 Step, Agent 매핑, on_fail 라우팅 표시 |
| Agent 팔레트 | 하단 Agent 목록에 6개 Agent(PMAgent, ReqAgent, ValidatorAgent, TestAgent, CodeAgent, CoordAgent)의 role, inputs, outputs 표시 |
| 기본 파이프라인 보호 | `full_spiral`의 Edit/Delete 버튼 비활성화 확인 |
| 파이프라인 복제 | "Clone" 버튼 → 새 이름 입력 → 복제 생성 |
| 파이프라인 검증 | "Validate" 버튼 → ValidationBanner(경고/에러) + ArtifactFlow 다이어그램 표시 |
| 커스텀 파이프라인 삭제 | 복제한 파이프라인에서 "Delete" → 확인 다이얼로그 |

### 3-4. 파이프라인 에디터

**경로:** `/pipelines/new` (새로 만들기) 또는 `/pipelines/:name/edit` (편집)

| 확인 항목 | 방법 |
|-----------|------|
| 새 파이프라인 생성 | `/pipelines` → "New Pipeline" 버튼 |
| 메타데이터 입력 | Name, Description, Max Iterations, Max Reworks per Gate 필드 |
| Step 추가 | "Add Step" 버튼 → Agent 선택 드롭다운 |
| Agent 정보 | AgentPicker에서 각 Agent의 role, inputs, outputs 툴팁 확인 |
| Step 설정 | Provider(anthropic/google/openai), Model, Max Tokens 입력 |
| TestAgent 모드 | TestAgent 선택 시 mode(design/execution) 드롭다운 표시 확인 |
| 드래그 앤 드롭 | Step 카드의 드래그 핸들로 순서 변경 |
| Step 삭제 | 각 Step 카드의 삭제 버튼 |
| 저장 | "Save" 클릭 → 409(이름 중복) / 403(기본 파이프라인) 에러 처리 확인 |
| 기존 파이프라인 편집 | `/pipelines/:name/edit` 접근 시 기존 설정이 로드되는지 확인 |

### 3-5. Run 실행

**경로:** `/runs/new`

| 확인 항목 | 방법 |
|-----------|------|
| User Story 입력 | 텍스트 영역에 요구사항 작성 (예: "할 일 관리 앱을 만들어줘") |
| 파이프라인 선택 | 드롭다운에서 파이프라인 선택 |
| 프로젝트 지정 (선택) | 드롭다운에서 프로젝트 선택 (없으면 독립 Run) |
| 고급 설정 | "Advanced Settings" 펼치기 → Max Iterations 슬라이더(1~10) 조정 |
| 실행 전 검증 | "Start Run" 클릭 → 파이프라인 자동 검증 실행 |
| 검증 경고 처리 | 경고 발생 시 "무시하고 실행" 확인 다이얼로그 표시 |
| 검증 에러 처리 | 에러 발생 시 실행 차단, 에러 목록 인라인 표시 |
| 동시 실행 제한 | 503/429 응답 시 "최대 실행 수 도달" 안내 |

> **참고:** 실제 Run 실행은 LLM API 키가 설정되어 있어야 동작한다.

### 3-6. Run 실시간 모니터링

**경로:** `/runs/:runId`

이 페이지는 Run 실행 중과 완료 후 모두 확인할 수 있다.

#### 실행 중 (SSE 실시간 스트리밍)

| 확인 항목 | 방법 |
|-----------|------|
| 연결 상태 | 상단에 Connected(초록) / Reconnecting(노랑) / Disconnected(빨강) 표시 |
| 진행률 바 | `Iteration N / max` — `Step M / total` 실시간 업데이트 |
| 현재 Agent 표시 | 실행 중인 Agent 이름 + 스피너 애니메이션 |
| 경과 시간 | 1초 단위 실시간 표시 |
| Narrative 대화방 | 우측 패널에 Agent별 메시지가 실시간 스트리밍 |
| Agent 아바타 | Agent별 고유 색상 아바타 표시 |
| Step 전환 | "Step N: AgentName" 구분 헤더 자동 삽입 |
| 자동 스크롤 | 새 메시지 시 자동 하단 스크롤 (위로 스크롤하면 일시 중지) |
| Rework 표시 | Validator 실패 시 "REWORK TRIGGERED" 구분선 표시 |
| Step 타임라인 | 좌측에 세로 타임라인: 완료(초록/빨강)/진행중(파란 pulse)/대기(회색) |
| 실행 취소 | "Cancel" 버튼 → 확인 다이얼로그 → 현재 Step 완료 후 중단 |

#### 완료 후 (JSON 리플레이)

| 확인 항목 | 방법 |
|-----------|------|
| 전체 이벤트 리플레이 | 완료된 Run 접근 시 DB에 저장된 이벤트가 일괄 로드 |
| Iteration 탭 | 여러 Iteration이 있을 경우 탭으로 전환 |
| Step 상세 | 타임라인에서 Step 클릭 → model, provider, 토큰 사용량 표시 |
| Resume | 실패/취소된 Run에서 "Resume" 버튼 → 이어서 실행 (새 Run 생성) |
| Clone | "Clone Run" → 동일 설정으로 새 Run 시작 |
| 산출물 링크 | "View Artifacts" → 산출물 페이지 이동 |
| 사용량 링크 | "View Usage" → 토큰 사용량 페이지 이동 |

### 3-7. 산출물 뷰어 (Artifacts)

**경로:** `/runs/:runId/artifacts`

| 확인 항목 | 방법 |
|-----------|------|
| Iteration 선택 | 좌측에서 Iteration 번호 선택 (기본: 최신) |
| Artifacts 탭 | YAML 아티팩트 목록 (UseCaseModel, ValidationReport, Implementation 등) |
| YAML 구문 강조 | Shiki 기반 YAML 하이라이팅 표시 |
| 복사 버튼 | 아티팩트 우측 상단 복사 버튼으로 클립보드 복사 |
| Code Files 탭 | 생성된 코드 파일 트리 구조 표시 |
| 파일 트리 탐색 | 디렉토리 접기/펼치기, 파일 클릭 시 우측에 코드 표시 |
| 언어별 하이라이팅 | JavaScript, CSS, HTML 등 파일 확장자에 따른 구문 강조 |

### 3-8. 토큰 사용량 분석 (Usage)

**경로:** `/runs/:runId/usage` 또는 `/projects/:projectId/usage`

| 확인 항목 | 방법 |
|-----------|------|
| 토큰 요약 카드 | Input, Output, Cache Read, Cache Creation, Total 5개 카드 |
| 모델별 파이 차트 | 모델별 토큰 사용 비율 (Pie Chart) |
| Agent별 막대 차트 | Agent별 Input/Output 토큰 비교 (Bar Chart) |
| Iteration별 라인 차트 | Iteration이 2개 이상일 때 추세 표시 (Line Chart) |
| 프로젝트 사용량 | `/projects/:projectId/usage` → 전체 Run 집계 + 파이프라인별 breakdown |

### 3-9. 설정 (Settings)

**경로:** `/settings`

| 확인 항목 | 방법 |
|-----------|------|
| 테마 전환 | Light / Dark / System 버튼 → 즉시 반영 확인 |
| API Key 설정 | API Key 입력 → 저장 → localStorage에 영속 저장 |
| 시스템 정보 | Backend 상태, 현재 LLM Provider/Model 표시 (Health API 연동) |

### 3-10. 반응형 레이아웃

| 확인 항목 | 방법 |
|-----------|------|
| 모바일 사이드바 | 브라우저 폭을 768px 이하로 줄이기 → 사이드바가 숨겨지고 햄버거 메뉴 표시 |
| Sheet 오버레이 | 햄버거 메뉴 클릭 → 슬라이드 오버레이로 네비게이션 표시 |
| 네비게이션 자동 닫힘 | 모바일에서 메뉴 항목 클릭 시 Sheet 자동 닫힘 |
| 콘텐츠 패딩 | 모바일에서 패딩 축소 (p-4), 데스크톱에서 확대 (p-6) |

### 3-11. API Key 인증 (Backend 보호 모드)

Backend에 `OPENSDLC_API_KEY` 환경변수를 설정하면 인증이 활성화된다.

```bash
# backend/.env
OPENSDLC_API_KEY=my-secret-key
```

| 확인 항목 | 방법 |
|-----------|------|
| 401 인터셉트 | API Key 미설정 상태에서 API 호출 시 자동으로 API Key 입력 다이얼로그 표시 |
| 에러 토스트 | 403(접근 거부), 404(리소스 없음), 500(서버 에러) 등 상태별 토스트 메시지 |
| 네트워크 에러 | Backend 미실행 상태 → "서버에 연결할 수 없습니다" 토스트 + 자동 재시도 (3회) |

---

## 4. LLM 없이 확인 가능한 기능

LLM API 키가 없어도 다음 기능은 모두 동작한다:

- 프로젝트 CRUD (생성, 조회, 수정, 삭제)
- 파이프라인 목록/상세 조회
- 파이프라인 복제, 편집, 삭제
- 파이프라인 검증 (Validate)
- 파이프라인 에디터 (드래그 앤 드롭, Agent 선택)
- Agent 팔레트 조회 (role, inputs, outputs)
- Run 시작 화면 (폼 입력, 검증까지 — 실행 시점에서 LLM 필요)
- 설정 페이지 (테마, API Key, 시스템 정보)
- 반응형 레이아웃
- 다크/라이트 모드

---

## 5. 빌드 및 타입 검사

```bash
cd frontend

# TypeScript 타입 검사
npx tsc -b

# 프로덕션 빌드
npm run build

# 빌드 결과 미리보기 (포트 4173)
npm run preview
```

주요 빌드 청크 (코드 스플리팅):

| 청크 | 크기 | 로드 시점 |
|------|------|-----------|
| shiki | ~9.5MB (gzip 1.6MB) | `/runs/:runId/artifacts` 진입 시 |
| recharts | ~382KB (gzip 110KB) | `/runs/:runId/usage` 진입 시 |
| radix | ~123KB (gzip 39KB) | 공유 UI 컴포넌트 |

---

## 6. 프론트엔드 라우트 전체 목록

| 경로 | 페이지 | 설명 |
|------|--------|------|
| `/` | DashboardPage | 대시보드 — 프로젝트 목록, 최근 Run |
| `/projects/:projectId` | DashboardPage | 프로젝트별 대시보드 |
| `/projects/:projectId/settings` | ProjectSettingsPage | 프로젝트 수정/삭제 |
| `/projects/:projectId/usage` | UsagePage | 프로젝트 토큰 사용량 |
| `/pipelines` | PipelinePage | 파이프라인 목록 |
| `/pipelines/:name` | PipelinePage | 파이프라인 상세 |
| `/pipelines/new` | PipelineEditorPage | 새 파이프라인 생성 |
| `/pipelines/:name/edit` | PipelineEditorPage | 파이프라인 편집 |
| `/runs/new` | RunStartPage | Run 실행 시작 |
| `/runs/:runId` | RunPage | Run 실시간 모니터링 / 리플레이 |
| `/runs/:runId/artifacts` | ArtifactsPage | 산출물 YAML + 코드 뷰어 |
| `/runs/:runId/usage` | UsagePage | Run 토큰 사용량 |
| `/settings` | SettingsPage | 테마, API Key, 시스템 정보 |

---

## 7. 환경변수 참조

Frontend 자체에 환경변수는 없다. 모든 설정은 Backend 환경변수로 제어된다.

| 변수 | 기본값 | 영향 |
|------|--------|------|
| `OPENSDLC_LLM_PROVIDER` | `google` | Health API에 표시되는 LLM 프로바이더 |
| `OPENSDLC_MODEL` | 프로바이더 기본 | Health API에 표시되는 모델명 |
| `OPENSDLC_API_KEY` | (빈 문자열) | 비어 있으면 인증 비활성, 설정 시 X-API-Key 헤더 필요 |
| `OPENSDLC_CORS_ORIGINS` | `*` | CORS 허용 오리진 (프로덕션에서 제한 필요) |
| `OPENSDLC_DATA_DIR` | `backend/data` | DB 및 아티팩트 저장 경로 |

---

## 8. 트러블슈팅

### Backend 연결 실패

```
"서버에 연결할 수 없습니다" 토스트가 반복 표시됨
```

→ Backend가 `http://localhost:8000`에서 실행 중인지 확인. `curl http://localhost:8000/api/health`로 테스트.

### DB 스키마 에러 (500 Internal Server Error)

```
sqlite3.OperationalError: no such column: runs.webhook_url
```

→ 기존 DB에 마이그레이션이 적용되지 않은 경우. DB 파일을 삭제하고 Backend 재시작:

```bash
rm backend/data/opensdlc.db
# Backend 재시작 → Alembic 마이그레이션 자동 실행
```

### TypeScript 타입 에러

```bash
npx tsc -b
```

에러가 있으면 빌드 전에 수정 필요. `npm run build`는 `tsc -b && vite build`를 순차 실행한다.

### 포트 충돌

```bash
# 사용 중인 포트 확인
lsof -i :8000   # Backend
lsof -i :5173   # Frontend

# 프로세스 종료
kill $(lsof -t -i:8000)
kill $(lsof -t -i:5173)
```
