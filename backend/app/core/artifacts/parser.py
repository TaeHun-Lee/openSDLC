"""Parse and extract YAML artifacts from LLM responses."""

from __future__ import annotations

import re
import logging
import textwrap
from typing import TypedDict
import yaml

logger = logging.getLogger(__name__)


class ParsedStepOutput(TypedDict):
    narrative: str
    artifact_yaml: str
    report_body: str


class ParsedArtifact(TypedDict):
    data: dict | None
    raw_yaml: str
    valid: bool
    error: str
    recovered: bool

# ---------------------------------------------------------------------------
# Code block extraction from narrative (<!-- FILE: path --> markers)
# ---------------------------------------------------------------------------

_FILE_MARKER_RE = re.compile(
    r"<!--\s*FILE:\s*(.+?)\s*-->\s*\n"   # <!-- FILE: path -->
    r"```([^\n]*?)\s*\n"                   # ```language
    r"(.*?)"                               # content (non-greedy)
    r"\n```",                              # closing fence
    re.DOTALL,
)

# 추가: 잘린 코드 블럭용 정규식 (닫는 ``` 없이 문자열 끝까지)
_FILE_MARKER_TRUNCATED_RE = re.compile(
    r"<!--\s*FILE:\s*(.+?)\s*-->\s*\n"
    r"```([^\n]*?)\s*\n"
    r"((?:(?!```)[\s\S])*)$",              # 닫는 ``` 없이 끝까지 매칭
)

_FILE_BLOCK_RE = re.compile(
    r"<!--\s*FILE:\s*.+?\s*-->\s*\n```[^\n]*?\s*\n.*?\n```\s*\n?",
    re.DOTALL,
)

# 추가: 일반 코드 블럭 제거 정규식 (닫는 ``` 가 있는 완전한 블럭)
_BARE_CODE_BLOCK_RE = re.compile(
    r"```[^\n]*\n.*?\n```\s*\n?",
    re.DOTALL,
)

# 추가: 잘린(truncated) 코드 블럭 제거 정규식 (닫는 ``` 가 없는 불완전 블럭)
_TRUNCATED_CODE_BLOCK_RE = re.compile(
    r"```[^\n]*\n(?:(?!```)[\s\S])*$",
)


def extract_code_blocks_from_narrative(narrative: str) -> list[dict[str, str]]:
    """Extract code file blocks marked with ``<!-- FILE: path -->`` from narrative.

    완전한 코드 블럭(닫는 ``` 있음)을 우선 추출하고,
    응답 잘림으로 닫히지 않은 마지막 코드 블럭도 추출을 시도한다.

    Returns list of ``{"path": str, "language": str, "content": str}``.
    """
    results: list[dict[str, str]] = []
    matched_spans: list[tuple[int, int]] = []

    # 1단계: 완전한 코드 블럭 추출 (기존 로직)
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
            matched_spans.append((match.start(), match.end()))

    # 2단계: 잘린 코드 블럭 추출 (1단계에서 매칭되지 않은 것만)
    for match in _FILE_MARKER_TRUNCATED_RE.finditer(narrative):
        # 이미 완전한 블럭으로 추출된 범위와 겹치면 스킵
        start = match.start()
        if any(s <= start < e for s, e in matched_spans):
            continue
        file_path = match.group(1).strip().strip("\"'")
        language = match.group(2).strip()
        content = match.group(3).rstrip()
        if file_path and content:
            logger.warning(
                "Truncated code block detected for '%s' — extracting partial content (%d chars)",
                file_path, len(content),
            )
            results.append({
                "path": file_path,
                "language": language,
                "content": content,
            })

    return results


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


def split_narrative_and_yaml(response_text: str) -> tuple[str, str]:
    """Split LLM response into (narrative_text, yaml_artifact)."""
    # 1. Look for a markdown block containing 'artifact_id:'
    matches = list(re.finditer(r"```([^\n]*?)\s*\n(.*?)```", response_text, re.DOTALL))
    
    fence_match = None
    # Prefer blocks that are NOT marked as files
    for match in matches:
        prefix = response_text[:match.start()]
        if re.search(r"<!--\s*FILE:\s*[^>]+-->\s*$", prefix):
            continue
        if re.search(r"^\s*artifact_id:", match.group(2), re.MULTILINE):
            fence_match = match
            break

    # If not found, accept any block with artifact_id:
    if not fence_match:
        for match in matches:
            if re.search(r"^\s*artifact_id:", match.group(2), re.MULTILINE):
                fence_match = match
                break

    if fence_match:
        yaml_part = fence_match.group(2).strip()
        narrative = response_text[:fence_match.start()].strip()
        after = response_text[fence_match.end():].strip()
        if after:
            narrative = f"{narrative}\n{after}".strip() if narrative else after
        yaml_part = _strip_extra_documents(yaml_part)
        return narrative, yaml_part

    # 2. Line-based fallback
    lines = response_text.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("artifact_id:"):
            start_idx = i
            break

    if start_idx is not None:
        narrative = "\n".join(lines[:start_idx]).strip()
        yaml_part = "\n".join(lines[start_idx:]).strip()
        yaml_part = re.sub(r"```\s*$", "", yaml_part).strip()
        yaml_part = _strip_extra_documents(yaml_part)
        return narrative, yaml_part

    # 3. Final fallback: try parsing the whole thing
    text = response_text.strip()
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "artifact_id" in data:
            return "", _strip_extra_documents(text)
    except yaml.YAMLError:
        pass

    # 4. Last resort: split out the largest YAML dict block even without artifact_id.
    largest_yaml_block = ""
    largest_yaml_start = -1
    largest_yaml_end = -1
    for match in matches:
        prefix = response_text[:match.start()]
        if re.search(r"<!--\s*FILE:\s*[^>]+-->\s*$", prefix):
            continue
        block_content = match.group(2).strip()
        try:
            data = yaml.safe_load(block_content)
            if isinstance(data, dict) and len(block_content) > len(largest_yaml_block):
                largest_yaml_block = block_content
                largest_yaml_start = match.start()
                largest_yaml_end = match.end()
        except yaml.YAMLError:
            continue

    if largest_yaml_block:
        narrative = response_text[:largest_yaml_start].strip()
        after = response_text[largest_yaml_end:].strip()
        if after:
            narrative = f"{narrative}\n{after}".strip() if narrative else after
        return narrative, largest_yaml_block

    return text, ""


def parse_step_output(response_text: str, output_mode: str) -> ParsedStepOutput:
    """Parse an LLM response according to the step output contract."""
    if output_mode == "narrative_only":
        return {
            "narrative": response_text.strip(),
            "artifact_yaml": "",
            "report_body": "",
        }
    if output_mode == "markdown_report":
        return {
            "narrative": "",
            "artifact_yaml": "",
            "report_body": response_text.strip(),
        }

    narrative, artifact_yaml = split_narrative_and_yaml(response_text)
    return {
        "narrative": narrative,
        "artifact_yaml": artifact_yaml,
        "report_body": "",
    }


def extract_yaml_from_response(response_text: str) -> str:
    """Extract raw YAML string from LLM response."""
    _, yaml_part = split_narrative_and_yaml(response_text)
    return yaml_part


def _strip_extra_documents(yaml_text: str) -> str:
    """Keep only the first YAML document if multiple are present."""
    parts = re.split(r"\n---\s*\n", yaml_text, maxsplit=1)
    return parts[0].strip()


def parse_artifact(response_text: str, strict: bool = False) -> dict:
    """Parse LLM response into a Python dict (YAML artifact)."""
    yaml_str = extract_yaml_from_response(response_text)
    try:
        data = yaml.safe_load(yaml_str)
        if not isinstance(data, dict):
            raise ValueError(f"Parsed YAML is not a dict: {type(data)}")
        if strict:
            issues = validate_artifact_structure(data)
            if issues:
                raise ValueError("; ".join(issues))
        return data
    except yaml.YAMLError as exc:
        logger.warning("YAML parse error: %s — attempting indentation recovery", exc)
        # Recovery 1: fix inconsistent indentation (common LLM output issue)
        dedented = _normalize_yaml_indentation(yaml_str)
        if dedented != yaml_str:
            try:
                data = yaml.safe_load(dedented)
                if isinstance(data, dict):
                    logger.info("Indentation normalization recovery succeeded")
                    return data
            except yaml.YAMLError:
                pass

        logger.warning("Indentation recovery failed — attempting truncation recovery")
        # Recovery 2: drop lines from the end until it parses
        data = _try_parse_truncated(dedented)
        if data is not None:
            logger.info("Truncation recovery succeeded")
            return data
        logger.error("YAML parse failed even after recovery.\nRaw text:\n%s", yaml_str[:500])
        raise


def parse_artifact_checked(response_text: str, strict: bool = False) -> ParsedArtifact:
    """Parse artifact with structured validity metadata."""
    yaml_str = extract_yaml_from_response(response_text)
    if strict:
        narrative, artifact_yaml = split_narrative_and_yaml(response_text)
        if narrative and artifact_yaml:
            # 코드 블록(<!-- FILE: --> 마커 포함)과 일반 코드 펜스를 제거한 뒤
            # 순수 텍스트가 남아있는지 확인한다.
            # CodeAgent는 코드 파일을 narrative에 첨부하므로,
            # 코드 블록만 있는 경우는 "mixed" 위반으로 보지 않는다.
            stripped = strip_code_blocks_from_narrative(narrative)
            if stripped.strip():
                return {
                    "data": None,
                    "raw_yaml": artifact_yaml,
                    "valid": False,
                    "error": "Narrative and YAML artifact were mixed in one response",
                    "recovered": False,
                }
    try:
        data = parse_artifact(response_text, strict=strict)
        return {
            "data": data,
            "raw_yaml": yaml_str,
            "valid": True,
            "error": "",
            "recovered": False,
        }
    except Exception as exc:
        return {
            "data": None,
            "raw_yaml": yaml_str,
            "valid": False,
            "error": str(exc),
            "recovered": False,
        }


def validate_artifact_structure(
    artifact: dict,
    artifact_type: str | None = None,
) -> list[str]:
    """Check required top-level fields and basic type constraints."""
    issues: list[str] = []
    if not isinstance(artifact, dict):
        return ["Artifact must be a top-level mapping"]
    if "artifact_id" not in artifact:
        issues.append("Missing required field: artifact_id")
    if "artifact_type" not in artifact:
        issues.append("Missing required field: artifact_type")
    if artifact_type and artifact.get("artifact_type") not in (None, artifact_type):
        issues.append(f"artifact_type mismatch: expected {artifact_type}")
    if "iteration" in artifact and not isinstance(artifact["iteration"], int):
        issues.append("Field 'iteration' must be an integer")
    if "source_artifact_ids" in artifact and not isinstance(artifact["source_artifact_ids"], list):
        issues.append("Field 'source_artifact_ids' must be a list")
    return issues


def _normalize_yaml_indentation(yaml_str: str) -> str:
    """Fix inconsistent indentation where the first line has less indent than the rest.

    A common LLM output pattern:
        artifact_id: "X"
          artifact_type: "Y"    # ← extra 2-space indent
          iteration: 1          # ← extra 2-space indent

    This function detects when all non-empty lines after the first share a
    common leading whitespace that the first line lacks, and removes it.
    """
    lines = yaml_str.splitlines()
    if len(lines) < 2:
        return yaml_str

    first_indent = len(lines[0]) - len(lines[0].lstrip())

    # Compute the minimum indentation of subsequent non-empty lines
    subsequent_indents = []
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:  # skip blank lines
            subsequent_indents.append(len(line) - len(stripped))

    if not subsequent_indents:
        return yaml_str

    min_subsequent = min(subsequent_indents)

    # If subsequent lines are indented more than the first line, dedent them
    if min_subsequent > first_indent:
        excess = min_subsequent - first_indent
        fixed_lines = [lines[0]]
        for line in lines[1:]:
            if line.strip():  # non-empty: remove excess indent
                fixed_lines.append(line[excess:] if len(line) >= excess else line)
            else:
                fixed_lines.append(line)
        return "\n".join(fixed_lines)

    return yaml_str


def _try_parse_truncated(yaml_str: str) -> dict | None:
    """Attempt to recover a truncated YAML by progressively removing trailing lines."""
    lines = yaml_str.splitlines()
    for drop in range(1, min(21, len(lines))):
        candidate = "\n".join(lines[: len(lines) - drop])
        try:
            data = yaml.safe_load(candidate)
            if isinstance(data, dict):
                return data
        except yaml.YAMLError:
            continue
    return None


def get_validation_result(validation_report: dict | None, raw_yaml: str = "") -> str:
    """Extract validation_result field (pass/warning/fail)."""
    if isinstance(validation_report, dict):
        result = validation_report.get("validation_result", "")
        if result in ("pass", "warning", "fail"):
            return result

    if raw_yaml:
        m = re.search(r"validation_result:\s*[\"']?(pass|warning|fail)[\"']?", raw_yaml)
        if m:
            logger.info("validation_result extracted via regex fallback: %s", m.group(1))
            return m.group(1)

    logger.warning("Could not determine validation_result — defaulting to fail")
    return "fail"


def extract_artifact_id(yaml_str: str) -> str | None:
    """Extract artifact_id from a YAML artifact string."""
    m = re.search(r"artifact_id:\s*[\"']?([^\s\"']+)[\"']?", yaml_str)
    if m:
        return m.group(1)
    try:
        data = yaml.safe_load(yaml_str)
        if isinstance(data, dict):
            return data.get("artifact_id")
    except yaml.YAMLError:
        pass
    return None


def extract_iteration(yaml_str: str) -> int:
    """Extract iteration number from a YAML artifact string."""
    m = re.search(r"iteration:\s*(\d+)", yaml_str)
    if m:
        return int(m.group(1))
    return 1


def artifact_to_yaml_str(artifact: dict) -> str:
    """Serialize artifact dict back to YAML string."""
    return yaml.dump(artifact, allow_unicode=True, sort_keys=False)
