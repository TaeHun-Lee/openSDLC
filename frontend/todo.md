# Frontend TODO — 발견된 이슈 및 미구현 기능

> 2026-03-26 분석 기준. 파일:라인번호는 분석 시점 기준이며 코드 변경 시 달라질 수 있음.

---

## 1. 버그 및 이슈

### P0 — 즉시 수정

#### ~~1-1. RunPage SSE 연결 조건 및 displayStatus 로직 오류~~ ✅ 수정완료
- `displayStatus`: SSE 연결 전(idle)에도 DB 상태를 신뢰하도록 변경
- `isActive`: `pending` 상태도 포함
- `RunProgress` 표시 조건을 `displayStatus` 기반으로 통일

---

### P1 — 안정성 확보

#### ~~1-2. SSE 재연결에 exponential backoff 없음~~ ✅ 수정완료
- `BASE_RECONNECT_DELAY * 2^attempt + jitter` (최대 30초)로 변경

#### ~~1-3. SSE stalled connection 타임아웃 없음~~ ✅ 수정완료
- 30초간 데이터 없으면 연결 중단 후 자동 재연결

#### ~~1-4. PipelineEditor step ID 충돌 위험~~ ✅ 수정완료
- `Date.now()` → `crypto.randomUUID()`로 변경

#### ~~1-5. ProjectSettings render 내 state 초기화~~ ✅ 수정완료
- render 본문 내 조건부 setState → `useEffect`로 이동

#### ~~1-6. NarrativeStore 메시지 무한 증가~~ ✅ 수정완료
- `MAX_MESSAGES = 2000` sliding window 적용

#### ~~1-7. SSE 재연결 실패 시 원인 피드백 부재~~ ✅ 수정완료
- ConnectionStatus에서 `sse-store.error` 읽어 표시, 최대 재시도 초과 메시지 추가

---

### P2 — 품질 개선

#### ~~1-8. 404 fallback 라우트 없음~~ ✅ 수정완료
- `NotFoundPage` 컴포넌트 추가, `<Route path="*">` catch-all 라우트 적용

#### ~~1-9. Error Boundary 없음~~ ✅ 수정완료
- `RouteErrorBoundary` 클래스 컴포넌트를 `App.tsx`에 추가, 라우트 전체를 감싸 렌더링 에러 격리

#### ~~1-10. narrative-store resume 감지 로직 취약~~ ✅ 수정완료
- `.includes("resume")` → `event_type === "pipeline_resumed"` 명시적 타입 비교로 변경

#### ~~1-11. StepTransition JSON.parse() 타입 검증 없음~~ ✅ 수정완료
- `JSON.parse()` 결과를 `Record<string, unknown>`으로 캐스팅 후 `typeof` 타입 가드 적용

#### ~~1-12. TokenUsageChart `as never` 타입 캐스팅~~ ✅ 수정완료
- `as never` 제거, Recharts `label` prop에 정확한 타입 시그니처 적용

#### ~~1-13. CancelButton 에러 상태 미초기화~~ ✅ 수정완료
- Cancel 버튼 클릭 시 (다이얼로그 열기) `setErrorMsg(null)` 호출로 이전 에러 초기화

#### ~~1-14. MessageBubble data 타입 미정의~~ ✅ 수정완료
- `EventInfo`에 `data?: Record<string, unknown> | null` 필드 추가, `eventToMessage`에서 전달

#### ~~1-15. Shiki 동적 import 최적화~~ ✅ 수정완료
- `src/lib/shiki.ts`에 `createHighlighter` 인스턴스 싱글턴 캐싱, 두 Viewer에서 재사용

#### ~~1-16. ArtifactViewer/CodeViewer dangerouslySetInnerHTML~~ ✅ 수정완료
- `dompurify` 패키지 추가, Shiki HTML 출력을 `DOMPurify.sanitize()` 후 렌더링

#### ~~1-17. Sidebar 프로젝트 이름 truncation 시 tooltip 없음~~ ✅ 수정완료
- 프로젝트 NavLink를 `Tooltip` 컴포넌트로 감싸 전체 이름 표시

#### ~~1-18. RunStartPage 기본 파이프라인 하드코딩~~ ✅ 수정완료
- `useState("")` 초기값 + `useEffect`로 `is_default` 플래그 기반 자동 선택, 로딩 중 버튼 비활성화

#### 1-19. RunStartPage 파이프라인 검증 패턴 불일치 — 보류
- 기능상 문제 없음. mutation hook 통일은 향후 리팩토링 시 검토

#### ~~1-20. ApiKeyDialog 한/영 혼재~~ ✅ 수정완료
- 한국어 문자열을 영어로 통일

#### ~~1-21. 미사용 `useRunProgress` hook (dead code)~~ ✅ 수정완료
- `useRunProgress` 및 `ProgressInfo` 타입 삭제

---

## 2. 미구현 기능

### ~~필수~~ ✅ 완료

| 기능 | 설명 | 상태 |
|------|------|------|
| ~~Error Boundary~~ | 라우트/컴포넌트 레벨 에러 격리 | ✅ 1-9에서 수정 |
| ~~404 페이지~~ | 존재하지 않는 경로 대응 | ✅ 1-8에서 수정 |

### 권장

| 기능 | 설명 | 관련 파일 |
|------|------|-----------|
| 페이지네이션 | Run 목록, Artifact 목록이 많을 때 성능 저하 | `DashboardPage.tsx`, `ArtifactsPage.tsx` |
| Artifact 다운로드 | 개별 파일 다운로드 + "Download All" ZIP 묶음 다운로드 (JSZip 또는 Backend 엔드포인트) | `ArtifactViewer.tsx`, `CodeViewer.tsx`, `ArtifactsPage.tsx` |
| 브레드크럼 네비게이션 | 하위 페이지에서 현재 위치 계층 경로 표시 (예: `Runs > {runId} > Artifacts`) | `ArtifactsPage.tsx`, `UsagePage.tsx`, `ProjectSettingsPage.tsx` |
| 검색/필터 | Run, 파이프라인, 프로젝트 검색 | `DashboardPage.tsx`, `PipelinePage.tsx` |
| i18n 통일 | 한영 혼용 에러 메시지 → 단일 언어 또는 i18n 프레임워크 | `client.ts`, `ApiKeyDialog.tsx` 등 |
| Loading Skeleton | 데이터 로딩 시 스켈레톤 UI (현재 텍스트만 표시) | 각 페이지 |

### 선택

| 기능 | 설명 | 관련 파일 |
|------|------|-----------|
| Run 비교 | 서로 다른 Run의 artifact 비교 뷰 | 신규 |
| 탭 간 설정 동기화 | localStorage 변경 시 다른 탭에 반영 | `stores/settings-store.ts` |
| SSE exponential backoff | 재연결 간격 점진적 증가 | `use-sse-stream.ts` |
| Narrative 가상화 | 1000개+ 이벤트 시 성능 최적화 (react-window 등) | `NarrativePanel.tsx` |
| DropdownMenu 컴포넌트 | Agent 필터, 설정 메뉴용 (Radix 이미 설치됨) | `src/components/ui/` |
| Popover 컴포넌트 | Step 클릭 상세 정보용 | `src/components/ui/` |

---

## 3. 접근성(a11y) 개선

| 항목 | 위치 | 내용 |
|------|------|------|
| 색상만으로 상태 구분 | `RunList`, `ProgressTimeline` | 아이콘/텍스트 보조 필요 |
| ARIA label 누락 | 다수 버튼/입력 | 스크린 리더 대응 |
| 키보드 내비게이션 | `PipelineEditor` DnD | 키보드로 step 순서 변경 불가 |
| ProgressTimeline 도트 | `ProgressTimeline` | `aria-label="Step N: AgentName, verdict"` 추가 |
| NarrativePanel 메시지 영역 | `NarrativePanel` | `role="log"`, `aria-live="polite"` 추가 |
| RunStartPage 폼 요소 | `RunStartPage` | textarea, select에 `aria-label` 또는 `<label htmlFor>` 연결 |
| IconButton 텍스트 레이블 | 전체 | 아이콘만 있는 버튼에 `aria-label` 추가 |

---

## 4. 성능 주의사항

| 항목 | 위치 | 내용 |
|------|------|------|
| ~~Shiki highlighter 재생성~~ | `ArtifactViewer`, `CodeViewer` | ✅ `src/lib/shiki.ts` 싱글턴으로 해결 |
| Narrative 렌더링 | `NarrativePanel` | 대량 이벤트 시 가상화 필요 |
| Query staleTime | `queries/*.ts` | 기본 10초 — 상황별 조정 고려 |
