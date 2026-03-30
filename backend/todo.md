# Backend TODO — 발견된 이슈 및 미구현 기능

> 2026-03-26 분석 기준. 파일:라인번호는 분석 시점 기준이며 코드 변경 시 달라질 수 있음.

---

## 1. 테스트 보강 (명시 요청 시에만)

> CLAUDE.md 규칙에 따라 테스트 코드는 사용자 명시 요청 시에만 작성.

현재 11개 테스트 파일 존재. 추가 커버리지가 필요한 영역:

| 영역 | 설명 |
|------|------|
| `final_state` None 케이스 | runs.py 상세 조회 시 final_state 미설정 상태 |
| artifact 파일 누락 | 디스크 파일 없을 때 artifacts 엔드포인트 동작 |
| resume + max_reworks | 파이프라인 설정 변경 후 resume 시 동작 |
| 동시 실행 제한 | Semaphore 초과 시 503 응답 검증 |
| cache 토큰 집계 | by_model, by_agent, by_iteration에 cache 토큰 포함 검증 |

---

## 2. `code_files` 필드 제거 및 코드 블록 분리 추출 리팩토링

> **상태**: 미착수
> **작성일**: 2026-03-26
> **목적**: core/ 템플릿 규격 준수를 위해 ImplementationArtifact에서 비인가 `code_files` 필드를 제거하고, 코드 산출물을 LLM 응답의 narrative 영역에서 별도 추출하는 구조로 전환한다.

---

### 6.0 문제 정의 및 배경

#### 현재 상태
OpenSDLC의 CodeAgent는 ImplementationArtifact를 생성할 때 YAML 아티팩트 내부에 `code_files`라는 필드를 포함하여 소스코드를 전달한다.

```yaml
# 현재 CodeAgent가 생성하는 ImplementationArtifact (문제 있는 형태)
artifact_id: "IMPL-01"
artifact_type: "ImplementationArtifact"
files_changed:
  - "src/main.py"
code_files:          # ← 이 필드가 문제
  - path: "src/main.py"
    language: "python"
    content: |
      print("hello")
```

#### 문제점
1. **`code_files` 필드는 core/ 템플릿(`core/open-sdlc-engine/templates/artifacts/ImplementationArtifact.yaml`)에 정의되지 않은 비인가 확장 필드**이다.
2. ValidatorAgent는 ImplementationArtifact 템플릿을 "schema compliance 검증 기준"으로 system prompt에 주입받는다. 템플릿에 `code_files`가 없으므로 **schema violation으로 판정하여 반복적으로 fail**을 생성한다.
3. 이를 방지하기 위해 `code_files_extension_mandate.md`와 `adversarial_mandate.md`에 예외 규칙을 추가했으나, **system prompt 상단의 스키마 참조 지시가 하단의 mandate 예외 지시보다 강해서 LLM이 mandate를 무시**한다.
4. 최근 실행(run `11239bc5`)에서 9번의 ValidationReport 중 대부분이 `code_files`를 schema violation으로 fail 처리하였다 (실제 artifact: `backend/data/runs/11239bc5-dc9e-4bea-96c5-45629bf3ba2b/iteration-01/artifacts/` 참조).

#### 근본 원인: 프롬프트 구조에서의 지시 충돌
`backend/app/core/prompts/builder.py`의 `build_system_prompt()` 함수가 system prompt를 조립하는 순서:

| 순서 | 섹션 | builder.py 라인 | 내용 |
|------|------|-----------------|------|
| 1 | Common Rules + Agent Prompt | 32-37 | ValidatorAgent 역할 정의 |
| 2 | Output Template | 60-67 | ValidationReportArtifact (출력 포맷) |
| **3** | **Reference Templates** | **70-76** | **"Use this to verify schema compliance of ImplementationArtifact artifacts:" + 템플릿 (code_files 없음)** |
| 4 | Constitution | 86-88 | 거버넌스 원칙 |
| **5** | **Mandates** | **91-98** | **"code_files는 schema violation이 아니다"라는 예외 지시** |

3번(상단)에서 code_files 없는 템플릿을 schema compliance 기준으로 강하게 제시 → 5번(하단)의 예외 지시가 무시됨.

#### 해결 방향
`code_files` 필드를 아티팩트 YAML에서 완전히 제거하고, 코드 산출물은 LLM 응답의 narrative 영역에 마크다운 코드 블록으로 출력하게 한 후, 파서가 이를 별도로 추출한다.

```
[현재 구조]
LLM 응답 = narrative + YAML(artifact 메타데이터 + code_files)
                                         ↑ schema violation 유발

[변경 후 구조]
LLM 응답 = narrative(코드 블록 포함) + YAML(artifact 메타데이터만)
                ↑ 여기서 코드 추출           ↑ 템플릿 100% 준수
```

---

### 6.1 현재 `code_files` 데이터 흐름 (제거 대상)

아래는 현재 `code_files`가 시스템을 관통하는 전체 경로이다. 이 경로의 모든 접점을 수정해야 한다.

```
1. CodeAgent LLM 호출
   → LLM이 ImplementationArtifact YAML 안에 code_files 필드 포함하여 응답
   (지시: backend/app/core/prompts/mandates/code_file_mandate.md)

2. generic_agent.py (create_agent_node 내 node_fn)
   → split_narrative_and_yaml(response.text)  [parser.py:11]
   → narrative와 artifact_yaml 분리
   → artifact_yaml에 code_files가 포함된 상태로 전달
   → artifact_saver(iteration, agent, type, artifact_yaml)  [generic_agent.py:449]

3. run_manager.py (_artifact_saver 콜백)
   → artifact_yaml을 디스크에 저장 (artifacts/{step}_{type}.yaml)
   → DB Artifact 행 삽입
   → ImplementationArtifact인 경우:
     → write_code_files(artifact_yaml, workspace_dir)  [run_manager.py:458-471]
       → code_extractor.extract_code_files(yaml) → YAML 파싱 → code_files 추출
       → 각 파일을 runs/{run_id}/iteration-NN/workspace/ 에 기록
     → DB code_files 테이블에 행 삽입 (relative_path, file_path, size_bytes)

4. ValidatorAgent
   → message_strategies._strategy_validator()가 ImplementationArtifact YAML 전체를
     user message로 전달 (code_files 포함)
   → ValidatorAgent가 code_files를 schema violation으로 판정 → fail

5. PMAgent
   → message_strategies._strategy_pm_assessor()가 ImplementationArtifact YAML 전체를
     user message로 전달 (code_files 포함)
   → "위 ImplementationArtifact의 code_files 내 실제 코드를 직접 분석하라" 지시
     [message_strategies.py:159]

6. API 엔드포인트 (runs.py)
   → GET /api/runs/{id}/artifacts:
     → DB code_files 테이블에서 조회 [runs.py:303-318]
     → 각 파일을 디스크에서 읽어 CodeFileInfo(path, language, content) 반환
     → in-memory fallback: extract_code_files(artifact_yaml)로 YAML에서 직접 추출 [runs.py:332-340]
   → GET /api/runs/{id}: _build_iteration_info()에서 code_files 포함 [runs.py:80-87]
```

---

### 6.2 변경 후 목표 데이터 흐름

```
1. CodeAgent LLM 호출
   → LLM이 narrative 영역에 <!-- FILE: path --> 마커 + 마크다운 코드 블록으로 코드 출력
   → 아티팩트 YAML에는 code_files 필드 없음 (core/ 템플릿 100% 준수)

2. generic_agent.py (create_agent_node 내 node_fn)
   → split_narrative_and_yaml(response.text)  — 기존과 동일
   → narrative에서 코드 블록 추출: extract_code_blocks_from_narrative(narrative)  [NEW]
   → narrative에서 코드 블록 제거 → clean_narrative (이벤트/로그용)
   → artifact_saver(iteration, agent, type, artifact_yaml, code_blocks)  [시그니처 변경]

3. run_manager.py (_artifact_saver 콜백)
   → artifact_yaml 저장 (기존과 동일, 단 code_files 없음)
   → ImplementationArtifact인 경우:
     → write_code_blocks(code_blocks, workspace_dir)  [NEW — YAML 파싱 없이 직접 기록]
     → DB code_files 테이블에 행 삽입 (기존과 동일)

4. ValidatorAgent
   → artifact YAML만 수신 (code_files 없음) → 템플릿 준수 → schema violation 해소

5. PMAgent
   → ImplementationArtifact YAML + 별도 코드 컨텍스트를 수신
   → 코드 컨텍스트 소스: PipelineState의 latest_code_blocks 또는 디스크 파일

6. API 엔드포인트
   → DB code_files 테이블 조회 (기존과 동일)
   → YAML fallback(extract_code_files) 제거 → narrative fallback으로 교체
```

---

### 6.3 CodeAgent 출력 형식 규격

변경 후 CodeAgent는 아래 형식으로 응답한다:

~~~
[CodeAgent] 구현을 완료하였습니다. 생성된 소스코드는 아래와 같습니다.

<!-- FILE: src/main.py -->
```python
#!/usr/bin/env python3
"""Main entry point."""

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
```

<!-- FILE: src/utils.py -->
```python
def helper():
    return 42
```

```yaml
artifact_id: "IMPL-01"
artifact_type: "ImplementationArtifact"
iteration: 1
created_by: "CodeAgent"
status: "implemented"
summary: "Todo 앱 구현"
files_changed:
  - "src/main.py"
  - "src/utils.py"
runtime_info:
  entrypoint: "python src/main.py"
  test_url: "http://localhost:8000"
traceability:
  - use_case_id: "UC-01-01"
    implemented_by:
      - "src/main.py: main()"
```
~~~

**규칙**:
- 각 코드 블록 앞에 `<!-- FILE: {relative_path} -->` HTML 주석 마커 필수
- 코드 블록은 ` ```{language} ` 펜스 사용
- 아티팩트 YAML은 응답 마지막에 ` ```yaml ` 펜스로 감싸서 출력
- 아티팩트 YAML에는 `code_files` 필드를 포함하지 않음
- `files_changed`에 나열된 모든 파일은 코드 블록으로 존재해야 함

---

### 6.4 수정 대상 파일 목록 및 상세 변경 내용

> **참고**: core/ 디렉토리는 git submodule이며 읽기 전용이다. 절대 수정하지 않는다.
> 아래 파일 경로는 모두 `backend/` 기준이다.

---

#### TASK 1: `app/core/prompts/mandates/code_file_mandate.md` — 전면 재작성

**현재 내용** (35줄): CodeAgent에게 `code_files` YAML 필드를 포함하라고 지시.
**변경**: `<!-- FILE: -->` 마크다운 코드 블록 형식으로 코드를 출력하라고 지시.

작성할 내용:
```markdown
# CODE FILE OUTPUT MANDATE
아티팩트 YAML과 별도로, narrative 영역에 모든 소스코드 파일을 마크다운 코드 블록으로 출력하라.
아티팩트 YAML 안에 code_files 필드를 포함하지 마라.

## 출력 형식
각 코드 파일 앞에 반드시 HTML 주석 마커를 배치하라:

<!-- FILE: {relative_path} -->
```{language}
{complete source code}
```

## 규칙
1. files_changed에 나열된 모든 파일은 반드시 위 형식의 코드 블록으로 출력해야 한다.
2. 각 content는 COMPLETE 파일이어야 한다 — placeholder, "..." 생략, "# TODO" 스텁 금지.
3. 코드는 runtime_info.entrypoint 명령으로 즉시 실행 가능해야 한다.
4. 파일 경로는 상대 경로를 사용하라 (예: "src/app.py", 절대 경로 금지).
5. 진입점, 모듈, 설정 파일, requirements.txt 등 필요한 모든 파일을 포함하라.
6. import, type hints, 에러 처리를 생략하지 마라.
7. 아티팩트 YAML은 코드 블록 이후에 ```yaml 펜스로 감싸서 출력하라.
8. 아티팩트 YAML에는 code_files 필드를 절대 포함하지 마라.
```

---

#### TASK 2: `app/core/prompts/mandates/code_files_extension_mandate.md` — 삭제

**현재 내용** (25줄): ValidatorAgent에게 code_files를 schema violation으로 취급하지 말라는 예외 규칙.
**변경**: 파일 삭제. code_files가 아티팩트에서 제거되므로 이 mandate는 불필요.

---

#### TASK 3: `agent-config-overrides/ValidatorAgent.override.yaml` — mandate 참조 제거

**현재 내용**:
```yaml
mandate_files:
  - "adversarial_mandate.md"
  - "code_files_extension_mandate.md"   # ← 이 줄 제거
```

**변경**: `code_files_extension_mandate.md` 항목 제거.

---

#### TASK 4: `app/core/prompts/mandates/adversarial_mandate.md` — code_files NOTE 제거

**현재 내용** (16줄), 12-14줄:
```
   NOTE: Additional fields beyond the template (e.g., `code_files` in ImplementationArtifact)
   are runtime-authorized extensions and are NOT schema violations. Only MISSING required
   template fields count as schema non-compliance.
```

**변경**: 위 3줄(NOTE 블록) 제거. 나머지 내용은 유지.

---

#### TASK 5: `app/core/artifacts/parser.py` — 코드 블록 추출 함수 추가

**현재 상태**: `split_narrative_and_yaml()` 함수만 존재. narrative에서 코드 블록을 추출하는 기능 없음.

**추가할 함수**: `extract_code_blocks_from_narrative(narrative: str) -> list[dict[str, str]]`

```python
import re

# <!-- FILE: path --> 마커 뒤에 오는 코드 블록을 추출하는 패턴
_FILE_MARKER_RE = re.compile(
    r"<!--\s*FILE:\s*(.+?)\s*-->\s*\n"   # <!-- FILE: path -->
    r"```(\w*)\s*\n"                       # ```language
    r"(.*?)"                               # content (non-greedy)
    r"\n```",                              # closing fence
    re.DOTALL,
)

def extract_code_blocks_from_narrative(narrative: str) -> list[dict[str, str]]:
    """Extract code file blocks marked with <!-- FILE: path --> from narrative text.

    Returns list of {"path": str, "language": str, "content": str}.
    """
    results = []
    for match in _FILE_MARKER_RE.finditer(narrative):
        file_path = match.group(1).strip().strip("\"'")
        language = match.group(2).strip()
        content = match.group(3)
        if file_path and content:
            results.append({
                "path": file_path,
                "language": language,
                "content": content,
            })
    return results
```

**추가할 함수**: `strip_code_blocks_from_narrative(narrative: str) -> str`

코드 블록(FILE 마커 + 코드펜스)을 narrative에서 제거하여 순수 텍스트만 남긴다.
이는 EventBus로 전파되는 narrative 이벤트에 거대한 코드가 포함되지 않게 하기 위함이다.

```python
_FILE_BLOCK_RE = re.compile(
    r"<!--\s*FILE:\s*.+?\s*-->\s*\n```\w*\s*\n.*?\n```\s*\n?",
    re.DOTALL,
)

def strip_code_blocks_from_narrative(narrative: str) -> str:
    """Remove <!-- FILE: --> code blocks from narrative, leaving other text intact."""
    return _FILE_BLOCK_RE.sub("", narrative).strip()
```

---

#### TASK 6: `app/core/artifacts/code_extractor.py` — 추출 로직 변경

**현재 상태**:
- `extract_code_files(impl_artifact_yaml: str)` — YAML에서 code_files 파싱 (13-45줄)
- `write_code_files(impl_artifact_yaml: str, workspace_dir)` — YAML 파싱 후 디스크 기록 (56-86줄)
- `get_runtime_info(impl_artifact_yaml: str)` — runtime_info 추출 (89-97줄)

**변경**:

(a) `extract_code_files()` — 기존 함수는 하위 호환을 위해 유지하되, deprecated 주석 추가.
    이미 저장된 기존 runs의 YAML에는 code_files가 있을 수 있으므로 API fallback에서 사용.

(b) 새 함수 `write_code_blocks()` 추가:

```python
def write_code_blocks(
    code_blocks: list[dict[str, str]],
    workspace_dir: str | Path,
) -> list[Path]:
    """Write pre-extracted code blocks to disk.

    Args:
        code_blocks: list of {"path": str, "language": str, "content": str}
                     (output of parser.extract_code_blocks_from_narrative)
        workspace_dir: target directory for code files

    Returns:
        List of written file paths.
    """
    workspace = Path(workspace_dir)
    if not code_blocks:
        return []

    written: list[Path] = []
    for entry in code_blocks:
        rel_path = _strip_workspace_prefix(entry["path"])
        content = entry["content"]

        try:
            resolved = (workspace / rel_path).resolve()
            if not str(resolved).startswith(str(workspace.resolve())):
                logger.error("Path traversal detected, skipping: %s", rel_path)
                continue
        except (ValueError, OSError) as exc:
            logger.error("Invalid path '%s': %s", rel_path, exc)
            continue

        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        written.append(resolved)
        logger.info("Written: %s (%d chars)", resolved, len(content))

    return written
```

(c) `get_runtime_info()` — 변경 없음 (artifact YAML에서 runtime_info를 읽으며, 이 필드는 템플릿에 존재).

---

#### TASK 7: `app/core/executor/generic_agent.py` — narrative에서 코드 블록 추출 + saver 연결

**현재 상태** (핵심 흐름, node_fn 내부):
```python
# 319줄
narrative, artifact_yaml = split_narrative_and_yaml(response.text)

# 322-334줄: narrative를 포매팅하여 이벤트로 전파

# 446-449줄: artifact 저장
saver = get_artifact_saver()
if saver and artifact_yaml:
    saver(state["iteration_count"], step.agent, resolved_output_type, artifact_yaml)
```

**변경**:

(a) import 추가:
```python
from app.core.artifacts.parser import (
    split_narrative_and_yaml,
    parse_artifact,
    get_validation_result,
    extract_code_blocks_from_narrative,    # NEW
    strip_code_blocks_from_narrative,       # NEW
)
```

(b) 319줄 이후에 코드 블록 추출 로직 추가:
```python
narrative, artifact_yaml = split_narrative_and_yaml(response.text)

# NEW: narrative에서 코드 블록 추출 (ImplementationArtifact인 경우)
code_blocks: list[dict[str, str]] = []
if resolved_output_type.startswith("ImplementationArtifact"):
    code_blocks = extract_code_blocks_from_narrative(narrative)
    if code_blocks:
        logger.info(
            "[%s] Extracted %d code blocks from narrative",
            step.agent, len(code_blocks),
        )
    # narrative에서 코드 블록 제거 (이벤트/로그용)
    narrative = strip_code_blocks_from_narrative(narrative)
```

(c) 446-449줄의 saver 호출 변경:
```python
saver = get_artifact_saver()
if saver and artifact_yaml:
    saver(state["iteration_count"], step.agent, resolved_output_type, artifact_yaml, code_blocks)
```

---

#### TASK 8: `app/services/print_capture.py` — artifact_saver 타입 힌트 확인

**확인 필요**: `get_artifact_saver()` / `set_artifact_saver()`의 콜백 타입 힌트가 있다면, code_blocks 파라미터를 추가해야 한다.

현재 시그니처 확인 후 `Callable[[int, str, str, str, list[dict[str, str]]], None]`으로 변경하거나, code_blocks에 기본값 `None`을 사용.

---

#### TASK 9: `app/services/run_manager.py` — artifact_saver 콜백 수정

**현재 상태** (`_artifact_saver` 또는 `_make_run_callbacks` 내부, 432-489줄 부근):
```python
def artifact_saver(iter_num, agent_name, artifact_type, artifact_yaml):
    # ... artifact 저장 ...
    if artifact_type.startswith("ImplementationArtifact"):
        workspace_dir = get_runs_dir() / run_id / f"iteration-{iter_num:02d}" / "workspace"
        written = write_code_files(artifact_yaml, workspace_dir)  # YAML에서 추출
        # ... DB 저장 ...
```

**변경**:
```python
def artifact_saver(iter_num, agent_name, artifact_type, artifact_yaml, code_blocks=None):
    # ... artifact 저장 (기존과 동일) ...
    if artifact_type.startswith("ImplementationArtifact") and code_blocks:
        workspace_dir = get_runs_dir() / run_id / f"iteration-{iter_num:02d}" / "workspace"
        written = write_code_blocks(code_blocks, workspace_dir)  # narrative에서 추출된 블록 직접 기록
        with self._session_factory() as session:
            for fpath in written:
                rel = str(fpath.relative_to(workspace_dir))
                repo.insert_code_file(
                    session,
                    run_id=run_id,
                    iteration_num=iter_num,
                    relative_path=rel,
                    file_path=str(fpath),
                    size_bytes=fpath.stat().st_size,
                )
```

import 변경:
```python
# 기존
from app.core.artifacts.code_extractor import write_code_files, get_runtime_info
# 변경
from app.core.artifacts.code_extractor import write_code_blocks, get_runtime_info
```

---

#### TASK 10: `app/core/prompts/message_strategies.py` — PMAgent 코드 접근 방식 변경

**현재 상태** (`_strategy_pm_assessor`, 119-186줄):
- 148-150줄: `latest_artifacts`에서 ImplementationArtifact YAML을 그대로 전달 (code_files 포함)
- 159줄: "위 ImplementationArtifact의 code_files 내 실제 코드를 직접 분석하라"

**변경**:
code_files가 아티팩트에서 제거되므로 PMAgent에 코드를 전달하는 별도 메커니즘이 필요하다.

**방안 A — PipelineState 확장** (권장):
`PipelineState`에 `latest_code_blocks: dict[str, str]` 필드를 추가하여, CodeAgent 실행 후 코드 원문을 별도 저장한다. pm_assessor 전략에서 이를 참조한다.

`app/core/pipeline/state.py`의 `PipelineState` TypedDict에 추가:
```python
class PipelineState(TypedDict):
    # ... 기존 필드 ...
    latest_code_blocks: dict[str, str]  # NEW: agent_id → 코드 블록 텍스트 (FILE 마커 포함)
```

`generic_agent.py`에서 state 업데이트 시 코드 블록 원문을 저장:
```python
# 코드 블록을 원문 그대로 state에 저장 (PMAgent 등 다운스트림용)
new_code_blocks = {**state.get("latest_code_blocks", {})}
if code_blocks:
    # FILE 마커 + 코드펜스 형태의 원문을 재구성하여 저장
    code_text_parts = []
    for block in code_blocks:
        code_text_parts.append(f"<!-- FILE: {block['path']} -->\n```{block['language']}\n{block['content']}\n```")
    new_code_blocks[step.agent] = "\n\n".join(code_text_parts)

state_update["latest_code_blocks"] = new_code_blocks
```

`_strategy_pm_assessor`에서 코드 컨텍스트 주입:
```python
# 기존 artifact 전달 코드 이후에 추가
code_context = state.get("latest_code_blocks", {}).get("CodeAgent", "")
if code_context:
    parts.append(f"--- 구현 소스코드 ---\n{code_context}\n")

# 159줄 변경
# 기존: "위 ImplementationArtifact의 code_files 내 실제 코드를 직접 분석하라.\n"
# 변경: "위 '구현 소스코드' 섹션의 실제 코드를 직접 분석하라.\n"
```

**TestAgent**도 동일한 방식으로 코드 컨텍스트 접근 가능:
`_strategy_test_agent`의 execution 모드에서:
```python
code_context = state.get("latest_code_blocks", {}).get("CodeAgent", "")
if code_context:
    # ImplementationArtifact 뒤에 코드 컨텍스트 추가
```

---

#### TASK 11: `app/routers/runs.py` — /artifacts 엔드포인트 수정

**현재 상태** (GET /{run_id}/artifacts, 275-347줄):
- 303-318줄: DB에서 code_files 조회 (정상 경로) — **변경 없음**
- 332-340줄: in-memory fallback에서 `extract_code_files(artifact_yaml)` 호출

**변경**:
- 332-340줄의 in-memory fallback: `extract_code_files()` 대신 narrative에서 코드 블록 추출

```python
# 기존 (in-memory fallback)
from app.core.artifacts.code_extractor import extract_code_files
code_entries = extract_code_files(impl_yaml)

# 변경 (in-memory fallback)
from app.core.artifacts.parser import extract_code_blocks_from_narrative
# active run의 narrative에서 코드 블록 추출
# 또는 PipelineState의 latest_code_blocks 참조
```

**주의**: 기존에 저장된 runs (code_files가 YAML에 포함된 데이터)에 대한 하위 호환을 위해, DB 조회가 비어있고 YAML에 code_files가 존재하면 기존 `extract_code_files()`를 fallback으로 사용한다.

```python
# 하위 호환 fallback 순서:
# 1. DB code_files 테이블 조회 (정상)
# 2. active run의 state에서 latest_code_blocks 조회 (신규 in-memory)
# 3. artifact YAML에서 extract_code_files() 조회 (레거시 하위 호환)
```

---

#### TASK 12: `app/core/pipeline/state.py` — PipelineState 확장

**변경**: `latest_code_blocks` 필드 추가.

```python
class PipelineState(TypedDict):
    user_story: str
    steps_completed: list[StepResult]
    latest_artifacts: dict[str, str]
    current_step_index: int
    iteration_count: int
    max_iterations: int
    rework_count: int
    max_reworks_per_gate: int
    pipeline_status: str
    latest_code_blocks: dict[str, str]  # NEW: agent_id → 코드 블록 원문
```

`graph_builder.py` 또는 `run_manager.py`에서 초기 state 생성 시 `latest_code_blocks: {}`를 포함해야 한다.

---

### 6.5 수정하지 않는 파일 (변경 없음 확인)

| 파일 | 이유 |
|------|------|
| `app/db/models.py` | CodeFile ORM 모델은 그대로 유지 (저장 구조 동일) |
| `app/db/repository.py` | insert_code_file(), list_code_files() 변경 없음 |
| `app/models/responses.py` | CodeFileInfo, CodeFileRef, RunArtifacts 모델 변경 없음 |
| `app/auth.py` | 무관 |
| `app/routers/health.py`, `agents.py`, `pipelines.py`, `projects.py` | 무관 |
| `core/*` (전체) | 읽기 전용 submodule, 절대 수정 금지 |

---

### 6.6 구현 순서 (의존성 기반)

```
Phase 1 — 코드 추출 인프라 (다른 변경의 전제 조건)
  [1] TASK 5: parser.py에 extract_code_blocks_from_narrative(), strip_code_blocks_from_narrative() 추가
  [2] TASK 6: code_extractor.py에 write_code_blocks() 추가
  [3] TASK 12: state.py에 latest_code_blocks 필드 추가

Phase 2 — 실행 파이프라인 연결 (Phase 1에 의존)
  [4] TASK 8: print_capture.py 타입 힌트 수정
  [5] TASK 7: generic_agent.py에서 narrative 코드 블록 추출 + saver 호출 변경
  [6] TASK 9: run_manager.py artifact_saver에 code_blocks 처리 추가

Phase 3 — Mandate/Prompt 변경 (Phase 2와 독립적이지만, 테스트 시 함께 적용)
  [7] TASK 1: code_file_mandate.md 재작성
  [8] TASK 2: code_files_extension_mandate.md 삭제
  [9] TASK 3: ValidatorAgent.override.yaml 수정
  [10] TASK 4: adversarial_mandate.md 수정

Phase 4 — 다운스트림 Agent 지원 (Phase 1, 3에 의존)
  [11] TASK 10: message_strategies.py PMAgent/TestAgent 코드 컨텍스트 주입

Phase 5 — API 호환 (Phase 2에 의존)
  [12] TASK 11: runs.py /artifacts 엔드포인트 fallback 변경
```

---

### 6.7 검증 체크리스트

구현 완료 후 아래 항목을 확인해야 한다:

- [ ] CodeAgent가 `<!-- FILE: -->` 마커 + 코드 블록 형식으로 코드를 출력하는가
- [ ] 아티팩트 YAML에 `code_files` 필드가 존재하지 않는가
- [ ] ValidatorAgent가 ImplementationArtifact를 schema violation 없이 검증하는가
- [ ] 코드 파일이 `runs/{run_id}/iteration-NN/workspace/`에 정상 기록되는가
- [ ] DB code_files 테이블에 행이 정상 삽입되는가
- [ ] PMAgent가 코드 컨텍스트에 접근하여 구현 완성도를 평가할 수 있는가
- [ ] TestAgent(execution mode)가 코드 컨텍스트에 접근할 수 있는가
- [ ] API GET /artifacts가 코드 파일을 정상 반환하는가
- [ ] 기존 runs (code_files가 YAML에 포함된 데이터)이 API에서 여전히 조회 가능한가
- [ ] `code_files_extension_mandate.md` 파일이 삭제되었는가
- [ ] `adversarial_mandate.md`에서 code_files NOTE가 제거되었는가

---

### 6.8 리스크 및 대응

| 리스크 | 설명 | 대응 |
|--------|------|------|
| LLM이 `<!-- FILE: -->` 마커를 정확히 출력하지 않을 수 있음 | 마커 없이 코드 블록만 출력하거나, 마커 형식이 다를 수 있음 | 폴백 파싱: `files_changed` 목록과 코드 블록 순서를 매핑하는 로직 추가 고려 |
| parser가 YAML 코드펜스와 소스코드 코드펜스를 혼동 | ` ```yaml `로 시작하는 아티팩트 블록과 ` ```python `으로 시작하는 코드 블록 | `<!-- FILE: -->` 마커가 있는 블록만 코드로 인식. `split_narrative_and_yaml()`은 마지막 yaml 블록을 아티팩트로 처리 (기존 로직) |
| PipelineState 크기 증가 | `latest_code_blocks`에 전체 소스코드가 저장됨 | 현재도 `latest_artifacts`에 code_files가 포함되어 있었으므로 총 크기는 유사. 필요 시 디스크 참조로 전환 |
| 기존 실행 데이터 하위 호환 | 이미 저장된 artifact YAML에 code_files 존재 | API에서 DB 조회 → narrative fallback → 레거시 YAML fallback 순서로 3단계 조회 |
