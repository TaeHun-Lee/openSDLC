# Agent Narrative 이슈 수정 명세

## 배경

Run `eda2e34f-08e6-47dc-a8f6-cd29d7aa56ba` (full_spiral 파이프라인) 분석에서 발견된 3가지 narrative 관련 이슈를 수정한다.

---

## 수정 대상 파일

| # | 파일 경로 | 이슈 |
|---|-----------|------|
| 1 | `backend/app/core/executor/generic_agent.py` | 이슈 1, 2, 3 |
| 2 | `backend/app/core/artifacts/parser.py` | 이슈 2 |

---

## 이슈 1: yaml_artifact 모드 Agent의 Narrative 미노출

### 증상
ReqAgent, TestAgent, CodeAgent 등 `output_mode == "yaml_artifact"` Agent가 narrative를 전혀 emit하지 않는다. DB의 Event 테이블에 해당 step의 `agent_narrative` 이벤트가 존재하지 않는다.

### 근본 원인
LLM이 YAML artifact만 반환하고 설명 텍스트를 앞에 쓰지 않으면, `parser.py`의 `split_narrative_and_yaml()`이 빈 문자열 narrative를 반환한다. 이후 `generic_agent.py:409`의 `if narrative:` 분기에서 falsy로 평가되어 `AGENT_NARRATIVE` 이벤트가 emit되지 않는다.

### 수정 내용

**파일**: `backend/app/core/executor/generic_agent.py`

**위치**: 408~423번 줄 — `# Terminal logging + narrative event` 블럭

**현재 코드**:
```python
        # Terminal logging + narrative event
        if narrative:
            formatted = _format_narrative(narrative, step.agent)
            print(f"\n{formatted}")
            _emit(RunEvent(
                event_type=EventType.AGENT_NARRATIVE,
                data={
                    "agent_id": step.agent,
                    "step_num": step.step,
                    "iteration_num": state["iteration_count"],
                    "rework_seq": _current_gate_rework_count(state, step),
                    "message": formatted,
                },
            ))
        else:
            print(f"\n[{step.agent}] Step {step.step} ({resolved_report_name or resolved_output_type})")
```

**수정 후 코드**:
```python
        # Terminal logging + narrative event
        if not narrative and resolved_output_mode == "yaml_artifact":
            # LLM이 YAML artifact만 반환하고 narrative를 쓰지 않은 경우
            # 기본 narrative를 생성하여 프론트엔드에 step 진행 상황을 전달한다
            mode_label = f" ({step.mode})" if step.mode else ""
            narrative = f"[{step.agent}] {resolved_output_type}{mode_label} 생성 완료"

        if narrative:
            formatted = _format_narrative(narrative, step.agent)
            print(f"\n{formatted}")
            _emit(RunEvent(
                event_type=EventType.AGENT_NARRATIVE,
                data={
                    "agent_id": step.agent,
                    "step_num": step.step,
                    "iteration_num": state["iteration_count"],
                    "rework_seq": _current_gate_rework_count(state, step),
                    "message": formatted,
                },
            ))
        else:
            print(f"\n[{step.agent}] Step {step.step} ({resolved_report_name or resolved_output_type})")
```

**변경 요약**:
- 기존 `if narrative:` 블럭 바로 위에 4줄의 fallback 로직을 추가한다.
- 조건: `not narrative and resolved_output_mode == "yaml_artifact"` — narrative가 비어있고 yaml_artifact 모드일 때만 적용.
- 생성되는 기본 narrative 형식: `"[{agent_id}] {output_type} 생성 완료"` (mode가 있으면 `" (design)"` 등 접미사 추가).
- `narrative_only`나 `markdown_report` 모드에는 영향 없음 — `narrative_only`는 응답 전체가 narrative이므로 빈 경우가 없고, `markdown_report`는 이슈 3에서 별도 처리.

---

## 이슈 2: narrative에 잔여 코드 펜스 마커(` ```yaml`) 노출

### 증상
Step 10 (rework된 TestAgent)의 `agent_narrative` 이벤트에 `[TestAgent] ```yaml` 이 포함되어 프론트엔드에 코드 펜스 열기 마커가 그대로 표시된다.

### 근본 원인
LLM 응답 구조: `"narrative 텍스트\n\n```yaml\nartifact_id: ...```"` 형태일 때,
`split_narrative_and_yaml()`이 ` ```yaml...``` ` 코드 펜스를 artifact로 분리하면서 narrative 부분에 불완전한 ` ```yaml` 줄이 잔류할 수 있다.

이후 `strip_code_blocks_from_narrative()`가 호출되지만, 현재 정규식들은 다음 경우를 처리하지 못한다:
- **고립된 코드 펜스 열기 마커**: ` ```yaml` 뒤에 내용 없이 줄만 존재하거나, ` ```yaml`이 narrative의 마지막 줄인 경우
- `_BARE_CODE_BLOCK_RE` (`r"```[^\n]*\n.*?\n```\s*\n?"`)는 열기+내용+닫기가 모두 있어야 매칭
- `_TRUNCATED_CODE_BLOCK_RE` (`r"```[^\n]*\n(?:(?!```)[\s\S])*$"`)는 ` ``` ` 뒤에 **최소 1줄 이상의 내용**이 있어야 매칭 (` \n` 이후 패턴 필요). ` ```yaml`이 마지막 줄이면 `\n` 이 없어 매칭 실패.

### 수정 내용

**파일**: `backend/app/core/artifacts/parser.py`

#### 수정 A: 고립된 코드 펜스 마커 제거 정규식 추가

**위치**: 58~60번 줄 (`_TRUNCATED_CODE_BLOCK_RE` 정의) 바로 아래에 새 정규식 추가

**추가할 코드** (60번 줄과 61번 줄 빈 줄 사이에 삽입):
```python
# 고립된 코드 펜스 열기 마커 (뒤에 내용 없이 줄 끝이거나 빈 줄만 남은 경우)
_ORPHAN_FENCE_RE = re.compile(
    r"^\s*```[^\n]*$",
    re.MULTILINE,
)
```

이 정규식은 다음을 매칭한다:
- ```` ```yaml ```` (줄의 시작, 선택적 공백, 코드 펜스 마커, 줄 끝)
- ```` ``` ```` (빈 코드 펜스)
- ```` ```json ```` 등 모든 언어 마커

#### 수정 B: `strip_code_blocks_from_narrative()` 함수에 고립 펜스 제거 단계 추가

**위치**: 155~166번 줄 — `strip_code_blocks_from_narrative` 함수

**현재 코드**:
```python
def strip_code_blocks_from_narrative(narrative: str) -> str:
    """Remove code blocks from narrative, leaving only plain text.

    제거 대상 (우선순위 순서):
    1. ``<!-- FILE: path -->`` 마커가 붙은 코드 블럭 (기존)
    2. 일반 코드 블럭 (`` ``` `` 로 열고 닫힌 완전한 블럭)
    3. 잘린 코드 블럭 (열린 `` ``` `` 는 있으나 닫는 `` ``` `` 이 없는 불완전 블럭)
    """
    result = _FILE_BLOCK_RE.sub("", narrative)
    result = _BARE_CODE_BLOCK_RE.sub("", result)
    result = _TRUNCATED_CODE_BLOCK_RE.sub("", result)
    return result.strip()
```

**수정 후 코드**:
```python
def strip_code_blocks_from_narrative(narrative: str) -> str:
    """Remove code blocks from narrative, leaving only plain text.

    제거 대상 (우선순위 순서):
    1. ``<!-- FILE: path -->`` 마커가 붙은 코드 블럭 (기존)
    2. 일반 코드 블럭 (`` ``` `` 로 열고 닫힌 완전한 블럭)
    3. 잘린 코드 블럭 (열린 `` ``` `` 는 있으나 닫는 `` ``` `` 이 없는 불완전 블럭)
    4. 고립된 코드 펜스 마커 (`` ``` `` 만 남은 줄)
    """
    result = _FILE_BLOCK_RE.sub("", narrative)
    result = _BARE_CODE_BLOCK_RE.sub("", result)
    result = _TRUNCATED_CODE_BLOCK_RE.sub("", result)
    result = _ORPHAN_FENCE_RE.sub("", result)
    return result.strip()
```

**변경 요약**:
- docstring에 4번 항목 추가: `4. 고립된 코드 펜스 마커 (`` ``` `` 만 남은 줄)`
- `return result.strip()` 바로 위에 `result = _ORPHAN_FENCE_RE.sub("", result)` 한 줄 추가.
- 실행 순서가 중요하다: 1→2→3 단계에서 완전한 블럭과 잘린 블럭을 먼저 제거한 뒤, 4단계에서 잔여 고립 마커를 청소한다. 만약 순서가 바뀌면 완전한 코드 블럭의 열기 마커가 먼저 제거되어 닫기 마커(` ``` `)가 고아로 남게 된다.

---

## 이슈 3: PMAgent Assessment narrative가 5줄로 잘림

### 증상
PMAgent의 마지막 Assessment step(Step 12/20)에서 `agent_narrative` 이벤트의 `message`가 report_body의 처음 5줄만 포함한다. Assessment 전문이 프론트엔드에 전달되지 않는다.

### 근본 원인
`generic_agent.py:403-406`에서 `markdown_report` 모드일 때 narrative를 의도적으로 5줄로 자른다:
```python
elif resolved_output_mode == "markdown_report" and report_body:
    summary_lines = [line.strip() for line in report_body.splitlines() if line.strip()][:5]
    narrative = "\n".join(summary_lines)
```

### 수정 내용

**파일**: `backend/app/core/executor/generic_agent.py`

**위치**: 403~406번 줄

**현재 코드**:
```python
        elif resolved_output_mode == "markdown_report" and report_body:
            # 비어있지 않은 줄 중 처음 5줄을 요약으로 사용 (기존 3줄 → 5줄)
            summary_lines = [line.strip() for line in report_body.splitlines() if line.strip()][:5]
            narrative = "\n".join(summary_lines)
```

**수정 후 코드**:
```python
        elif resolved_output_mode == "markdown_report" and report_body:
            # report_body 전체를 narrative로 사용한다.
            # 프론트엔드에서 접기/펼치기 등 UI 레벨로 표시 분량을 조절한다.
            narrative = report_body.strip()
```

**변경 요약**:
- `[:5]` 슬라이스로 5줄 제한하던 로직을 제거한다.
- `report_body.strip()`을 그대로 narrative에 대입한다.
- 이렇게 하면 `_format_narrative(narrative, step.agent)` 호출 시 각 줄에 `[PMAgent]` 접두사가 붙어 기존 포맷 규칙을 유지한다.
- SSE `agent_narrative` 이벤트의 `message` 필드에 assessment 전문이 포함된다.
- `step_result["report_body"]`에도 동일한 전문이 저장되므로 데이터 일관성이 유지된다.

---

## 수정 순서 및 적용 방법

### Step 1: `backend/app/core/artifacts/parser.py` 수정

1. 파일을 열고 58~60번 줄을 찾는다:
   ```python
   _TRUNCATED_CODE_BLOCK_RE = re.compile(
       r"```[^\n]*\n(?:(?!```)[\s\S])*$",
   )
   ```

2. 이 정의 바로 아래(60번 줄과 기존 빈 줄 사이)에 다음을 삽입한다:
   ```python

   # 고립된 코드 펜스 열기 마커 (뒤에 내용 없이 줄 끝이거나 빈 줄만 남은 경우)
   _ORPHAN_FENCE_RE = re.compile(
       r"^\s*```[^\n]*$",
       re.MULTILINE,
   )
   ```

3. `strip_code_blocks_from_narrative` 함수(155번 줄 부근)에서 `return result.strip()` 바로 위에 다음 줄을 추가한다:
   ```python
       result = _ORPHAN_FENCE_RE.sub("", result)
   ```

4. 같은 함수의 docstring에 4번 항목을 추가한다:
   ```
   4. 고립된 코드 펜스 마커 (`` ``` `` 만 남은 줄)
   ```

### Step 2: `backend/app/core/executor/generic_agent.py` 수정

1. 403~406번 줄을 찾아 5줄 제한 로직을 교체한다:

   **삭제**:
   ```python
        elif resolved_output_mode == "markdown_report" and report_body:
            # 비어있지 않은 줄 중 처음 5줄을 요약으로 사용 (기존 3줄 → 5줄)
            summary_lines = [line.strip() for line in report_body.splitlines() if line.strip()][:5]
            narrative = "\n".join(summary_lines)
   ```

   **삽입**:
   ```python
        elif resolved_output_mode == "markdown_report" and report_body:
            # report_body 전체를 narrative로 사용한다.
            # 프론트엔드에서 접기/펼치기 등 UI 레벨로 표시 분량을 조절한다.
            narrative = report_body.strip()
   ```

2. 408번 줄 부근의 `# Terminal logging + narrative event` 블럭을 찾아 `if narrative:` 바로 위에 fallback 로직을 추가한다:

   **현재**:
   ```python
        # Terminal logging + narrative event
        if narrative:
   ```

   **수정 후**:
   ```python
        # Terminal logging + narrative event
        if not narrative and resolved_output_mode == "yaml_artifact":
            # LLM이 YAML artifact만 반환하고 narrative를 쓰지 않은 경우
            # 기본 narrative를 생성하여 프론트엔드에 step 진행 상황을 전달한다
            mode_label = f" ({step.mode})" if step.mode else ""
            narrative = f"[{step.agent}] {resolved_output_type}{mode_label} 생성 완료"

        if narrative:
   ```

---

## 수정 후 검증 항목

| # | 검증 내용 | 확인 방법 |
|---|-----------|-----------|
| 1 | ReqAgent, TestAgent, CodeAgent step에서 `agent_narrative` 이벤트가 emit되는가 | SSE 스트림에서 해당 step의 `agent_narrative` 이벤트 존재 여부 확인 |
| 2 | narrative에 ` ```yaml` 등 코드 펜스 잔재가 포함되지 않는가 | `agent_narrative` 이벤트의 `message` 필드에 ` ``` ` 패턴이 없는지 확인 |
| 3 | PMAgent Assessment의 narrative가 5줄 이상(전문) 전달되는가 | `agent_narrative` 이벤트의 `message` 필드 줄 수가 6줄 이상인지 확인 |
| 4 | ValidatorAgent의 기존 narrative 동작이 변경되지 않는가 | ValidatorAgent step에서 `agent_narrative` + `validation_result` 이벤트 정상 emit 확인 |
| 5 | narrative_only 모드(PMAgent Initializer)의 동작이 변경되지 않는가 | Step 1 PMAgent의 `agent_narrative` 이벤트가 기존과 동일하게 emit되는지 확인 |
| 6 | 코드 블럭 추출(ImplementationArtifact)이 정상 동작하는가 | CodeAgent step에서 `code_blocks`가 정상 추출되고 artifact_saver로 저장되는지 확인 |

---

## 영향 범위

- **Backend SSE 이벤트**: `agent_narrative` 이벤트의 발생 빈도 증가 (기존에 누락되던 step들도 emit). `message` 필드의 데이터 크기 증가 (Assessment 전문 포함).
- **DB Event 테이블**: `agent_narrative` 타입 행이 더 많이 저장됨.
- **프론트엔드**: Assessment 전문이 전달되므로 긴 텍스트 표시를 위한 UI 대응 필요 (접기/펼치기 등).
- **PoC (`poc/`)**: 동일 구조이므로 같은 수정이 필요하지만, PoC는 CLI 출력 전용이므로 SSE 이벤트가 없어 이슈 1, 3의 체감 영향 없음. `strip_code_blocks_from_narrative`는 공유 로직이므로 이슈 2 수정은 PoC에도 적용 권장.
