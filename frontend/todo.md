# Frontend TODO — 발견된 이슈 및 미구현 기능

> 2026-03-31 분석 기준. 파일:라인번호는 분석 시점 기준이며 코드 변경 시 달라질 수 있음.

---

## 1. 미구현 기능

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
| Narrative 가상화 | 1000개+ 이벤트 시 성능 최적화 (react-window 등) | `NarrativePanel.tsx` |
| DropdownMenu 컴포넌트 | Agent 필터, 설정 메뉴용 (Radix 이미 설치됨) | `src/components/ui/` |
| Popover 컴포넌트 | Step 클릭 상세 정보용 | `src/components/ui/` |

---

## 2. 접근성(a11y) 개선

| 항목 | 위치 | 내용 |
|------|------|------|
| 색상만으로 상태 구분 | `RunList`, `ProgressTimeline` | 아이콘/텍스트 보조 필요 |
| ARIA label 누락 | 다수 버튼/입력 | 스크린 리더 대응 |
| ProgressTimeline 도트 | `ProgressTimeline` | `aria-label="Step N: AgentName, verdict"` 추가 |
| NarrativePanel 메시지 영역 | `NarrativePanel` | `role="log"`, `aria-live="polite"` 추가 |
| RunStartPage 폼 요소 | `RunStartPage` | textarea, select에 `aria-label` 또는 `<label htmlFor>` 연결 |
| IconButton 텍스트 레이블 | 전체 | 아이콘만 있는 버튼에 `aria-label` 추가 |

---

## 3. 성능 주의사항
- Narrative 렌더링: 대량 이벤트 시 가상화 필요 (`NarrativePanel.tsx`)
- Query staleTime: 기본 10초 — 상황별 조정 고려 (`queries/*.ts`)
