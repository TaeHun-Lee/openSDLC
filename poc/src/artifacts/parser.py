"""Parse and extract YAML artifacts from LLM responses."""

import re
import logging
import textwrap
import yaml

logger = logging.getLogger(__name__)


def split_narrative_and_yaml(response_text: str) -> tuple[str, str]:
    """Split LLM response into (narrative_text, yaml_artifact).

    The narrative is the agent's progress report / handoff announcement.
    The YAML is the structured artifact.
    Returns (narrative, yaml) where narrative may be empty.
    """
    # Try markdown code fence first
    fence_match = re.search(
        r"```(?:yaml)?\s*\n(.*?)```",
        response_text,
        re.DOTALL,
    )
    if fence_match:
        yaml_part = fence_match.group(1).strip()
        # Everything before the fence is narrative
        narrative = response_text[:fence_match.start()].strip()
        # Everything after the fence (if any) appended to narrative
        after = response_text[fence_match.end():].strip()
        if after:
            narrative = f"{narrative}\n{after}".strip() if narrative else after
        yaml_part = _strip_extra_documents(yaml_part)
        return narrative, yaml_part

    # Heuristic: look for a line starting with 'artifact_id:' and split there
    lines = response_text.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("artifact_id:"):
            start_idx = i
            break

    if start_idx is not None:
        narrative = "\n".join(lines[:start_idx]).strip()
        yaml_part = "\n".join(lines[start_idx:]).strip()
        yaml_part = _strip_extra_documents(yaml_part)
        return narrative, yaml_part

    # Fallback: no artifact_id found — check if it's actually YAML
    text = response_text.strip()
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "artifact_id" in data:
            # Valid YAML artifact without preceding narrative
            return "", _strip_extra_documents(text)
    except yaml.YAMLError:
        pass

    # Not a YAML artifact — treat entire response as narrative (e.g. PMAgent reports)
    return text, ""


def extract_yaml_from_response(response_text: str) -> str:
    """
    Extract raw YAML string from LLM response.

    Agents should output bare YAML (no markdown fences), but we handle
    the common case where the model wraps it in ```yaml ... ``` anyway.
    Also handles multi-document YAML (strips trailing ``---`` separators).
    """
    _, yaml_part = split_narrative_and_yaml(response_text)
    return yaml_part


def _strip_extra_documents(yaml_text: str) -> str:
    """Keep only the first YAML document if multiple are present."""
    # Split on document separator lines ('^---$' at line start)
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
    # Remove up to 20 lines from the end to find a parseable prefix
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
    """Extract validation_result field (pass/warning/fail).

    Falls back to regex extraction from raw YAML when the dict is None
    (e.g. when YAML parsing failed completely).
    """
    if isinstance(validation_report, dict):
        result = validation_report.get("validation_result", "")
        if result in ("pass", "warning", "fail"):
            return result

    # Regex fallback: search raw text for validation_result field
    if raw_yaml:
        m = re.search(r"validation_result:\s*[\"']?(pass|warning|fail)[\"']?", raw_yaml)
        if m:
            logger.info("validation_result extracted via regex fallback: %s", m.group(1))
            return m.group(1)

    logger.warning("Could not determine validation_result — defaulting to fail")
    return "fail"


def extract_artifact_id(yaml_str: str) -> str | None:
    """Extract artifact_id from a YAML artifact string.

    Tries regex first (fast), falls back to full YAML parse.
    Returns None if not found.
    """
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
    """Extract iteration number from a YAML artifact string.

    Returns 1 if not found or not parseable.
    """
    m = re.search(r"iteration:\s*(\d+)", yaml_str)
    if m:
        return int(m.group(1))
    return 1


def artifact_to_yaml_str(artifact: dict) -> str:
    """Serialize artifact dict back to YAML string."""
    return yaml.dump(artifact, allow_unicode=True, sort_keys=False)
