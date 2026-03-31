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
| 키보드 내비게이션 | `PipelineEditor` DnD | 키보드로 step 순서 변경 불가 |
| ProgressTimeline 도트 | `ProgressTimeline` | `aria-label="Step N: AgentName, verdict"` 추가 |
| NarrativePanel 메시지 영역 | `NarrativePanel` | `role="log"`, `aria-live="polite"` 추가 |
| RunStartPage 폼 요소 | `RunStartPage` | textarea, select에 `aria-label` 또는 `<label htmlFor>` 연결 |
| IconButton 텍스트 레이블 | 전체 | 아이콘만 있는 버튼에 `aria-label` 추가 |

---

## 3. 성능 주의사항
- Narrative 렌더링: 대량 이벤트 시 가상화 필요 (`NarrativePanel.tsx`)
- Query staleTime: 기본 10초 — 상황별 조정 고려 (`queries/*.ts`)

---

### 완료 (Completed)

#### P0~P1 — 버그 및 안정성 해결
- ✅ **1-1. RunPage SSE 연결/상태 로직**: DB 상태 신뢰도 및 `isActive` 조건 개선.
- ✅ **1-2. SSE Exponential Backoff**: 재연결 지연 시간 점진적 증가 로직 적용.
- ✅ **1-3. SSE Connection Timeout**: 30초 무응답 시 자동 재연결 처리.
- ✅ **1-4. PipelineEditor ID 충돌**: `crypto.randomUUID()`로 식별자 생성 방식 변경.
- ✅ **1-5. ProjectSettings State 초기화**: render 내 setState를 `useEffect`로 이전.
- ✅ **1-6. NarrativeStore 메모리 관리**: `MAX_MESSAGES` 슬라이딩 윈도우 적용.
- ✅ **1-7. SSE 에러 피드백**: 사용자 화면에 구체적인 연결 에러 메시지 표시.
- ✅ **1-8. 404 Fallback**: 존재하지 않는 경로에 대한 `NotFoundPage` 추가.
- ✅ **1-9. Error Boundary**: 라우트 레벨 에러 격리를 위한 Boundary 추가.
- ✅ **1-10. Resume 감지 개선**: 이벤트 타입 명시적 비교로 로직 안정화.

#### P2 — 품질 개선
- ✅ **1-11. JSON 파싱 안전성**: 타입 가드 추가로 런타임 에러 방지.
- ✅ **1-12. 차트 타입 캐스팅**: Recharts 관련 `as never` 제거 및 정확한 타입 지정.
- ✅ **1-13. 에러 상태 초기화**: Cancel 버튼 클릭 시 이전 에러 메시지 초기화.
- ✅ **1-14. 메시지 데이터 타입**: `EventInfo`에 확장 데이터 필드 추가.
- ✅ **1-15. Shiki 최적화**: highlighter 싱글턴 캐싱으로 성능 개선.
- ✅ **1-16. 보안 강화**: `dompurify`를 통한 HTML 출력물 새니타이징 적용.
- ✅ **1-17. UI/UX 개선**: 사이드바 툴팁 추가 및 프로젝트 이름 생략 대응.
- ✅ **1-18. 파이프라인 선택**: 기본 파이프라인 자동 선택 로직 구현.
- ✅ **1-20. i18n 정리**: API 키 다이얼로그 영문 통일.
- ✅ **1-21. Dead Code 제거**: 사용되지 않는 `useRunProgress` 훅 삭제.

#### 기능 구현 및 성능 최적화
- ✅ **Error Boundary & 404 페이지**: 서비스 안정성 및 경로 대응 완료.
- ✅ **SSE 점진적 재연결**: 네트워크 불안정 상황 대응 완료.
- ✅ **Shiki Highlighter 재사용**: 문법 강조 엔진 중복 생성 문제 해결 완료.
