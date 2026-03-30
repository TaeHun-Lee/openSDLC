"""Parse and extract YAML artifacts from LLM responses."""

from __future__ import annotations

import re
import logging
import textwrap
import yaml

logger = logging.getLogger(__name__)

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

_FILE_BLOCK_RE = re.compile(
    r"<!--\s*FILE:\s*.+?\s*-->\s*\n```[^\n]*?\s*\n.*?\n```\s*\n?",
    re.DOTALL,
)


def extract_code_blocks_from_narrative(narrative: str) -> list[dict[str, str]]:
    """Extract code file blocks marked with ``<!-- FILE: path -->`` from narrative.

    Returns list of ``{"path": str, "language": str, "content": str}``.
    """
    results: list[dict[str, str]] = []
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


def strip_code_blocks_from_narrative(narrative: str) -> str:
    """Remove ``<!-- FILE: -->`` code blocks from narrative, leaving other text."""
    return _FILE_BLOCK_RE.sub("", narrative).strip()


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

    return text, ""


def extract_yaml_from_response(response_text: str) -> str:
    """Extract raw YAML string from LLM response."""
    _, yaml_part = split_narrative_and_yaml(response_text)
    return yaml_part


def _strip_extra_documents(yaml_text: str) -> str:
    """Keep only the first YAML document if multiple are present."""
    parts = re.split(r"\n---\s*\n", yaml_text, maxsplit=1)
    return parts[0].strip()


def parse_artifact(response_text: str) -> dict:
    """Parse LLM response into a Python dict (YAML artifact)."""
    yaml_str = extract_yaml_from_response(response_text)
    try:
        data = yaml.safe_load(yaml_str)
        if not isinstance(data, dict):
            raise ValueError(f"Parsed YAML is not a dict: {type(data)}")
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
