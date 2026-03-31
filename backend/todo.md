# Backend TODO — 발견된 이슈 및 미구현 기능

> 2026-03-31 분석 기준. 파일:라인번호는 분석 시점 기준이며 코드 변경 시 달라질 수 있음.

---

## 1. 테스트 보강 (명시 요청 시에만)

> CLAUDE.md 규칙에 따라 테스트 코드는 사용자 명시 요청 시에만 작성.

현재 11개 테스트 파일 존재. 추가 커버리지가 필요한 영역:

| 영역 | 설명 |
|------|------|
| artifact 파일 누락 | 디스크 파일 없을 때 artifacts 엔드포인트 동작 |
| resume + max_reworks | 파이프라인 설정 변경 후 resume 시 동작 |

---

### 완료 (Completed)

#### [기능 및 리팩토링] `code_files` 필드 제거 및 코드 블록 분리 추출
- ✅ **TASK 1: code_file_mandate.md 전면 재작성**: LLM에게 HTML 주석 마커(`<!-- FILE: -->`) 형식을 사용하도록 지시 완료.
- ✅ **TASK 2: code_files_extension_mandate.md 삭제**: 불필요해진 예외 규칙 파일 제거 완료.
- ✅ **TASK 3: ValidatorAgent.override.yaml 수정**: mandate 참조 제거 완료.
- ✅ **TASK 4: adversarial_mandate.md 수정**: code_files 관련 예외 문구 제거 완료.
- ✅ **TASK 5: parser.py 코드 블록 추출 함수 추가**: `extract_code_blocks_from_narrative` 및 `strip_code_blocks_from_narrative` 구현 완료.
- ✅ **TASK 6: code_extractor.py 추출 로직 변경**: `write_code_blocks` 추가 및 YAML 기반 추출의 하위 호환성 유지 완료.
- ✅ **TASK 7: generic_agent.py 실행 흐름 연결**: narrative에서 코드 블록 추출 및 `artifact_saver` 전달 로직 구현 완료.
- ✅ **TASK 8: print_capture.py 타입 힌트 확인**: `artifact_saver` 콜백 파라미터(code_blocks) 추가 완료.
- ✅ **TASK 9: run_manager.py artifact_saver 콜백 수정**: 추출된 코드 블록을 워크스페이스에 저장하고 DB에 기록하는 로직 구현 완료.
- ✅ **TASK 10: message_strategies.py 코드 접근 방식 변경**: PMAgent 및 TestAgent에 코드 컨텍스트 주입 로직 구현 완료.
- ✅ **TASK 11: runs.py /artifacts 엔드포인트 수정**: narrative 기반 코드 추출 및 레거시 데이터 하위 호환(fallback) 처리 완료.
- ✅ **TASK 12: state.py PipelineState 확장**: `latest_code_blocks` 필드 추가 및 데이터 전파 구조 마련 완료.

#### [테스트 및 안정성]
- ✅ **동시 실행 제한**: `run_manager.py` 내 `asyncio.Semaphore`를 통한 동시 실행 제어 구현 완료.
- ✅ **cache 토큰 집계**: `test_usage.py`에서 `cache_read_tokens`, `cache_creation_tokens` 집계 검증 로직 구현 완료.
- ✅ **final_state None 케이스 처리**: `runs.py` 상세 조회 시 `final_state`가 미설정된 상태에서의 에러 방지 로직 구현 완료.
