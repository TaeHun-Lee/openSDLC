"""Parse and extract YAML artifacts from LLM responses."""

import re
import logging
import yaml

logger = logging.getLogger(__name__)


def extract_yaml_from_response(response_text: str) -> str:
    """
    Extract raw YAML string from LLM response.

    Agents should output bare YAML (no markdown fences), but we handle
    the common case where the model wraps it in ```yaml ... ``` anyway.
    Also handles multi-document YAML (strips trailing ``---`` separators).
    """
    # Try markdown code fence first
    fence_match = re.search(
        r"```(?:yaml)?\s*\n(.*?)```",
        response_text,
        re.DOTALL,
    )
    if fence_match:
        raw = fence_match.group(1).strip()
    else:
        # Heuristic: look for a line starting with 'artifact_id:' and take from there
        lines = response_text.splitlines()
        start_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("artifact_id:"):
                start_idx = i
                break

        if start_idx is not None:
            raw = "\n".join(lines[start_idx:]).strip()
        else:
            # Fallback: return full text and let yaml.safe_load decide
            raw = response_text.strip()

    # Strip trailing YAML document separators to avoid multi-document errors
    raw = _strip_extra_documents(raw)
    return raw


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
        logger.warning("YAML parse error: %s — attempting truncation recovery", exc)
        # Truncated YAML recovery: drop lines from the end until it parses
        data = _try_parse_truncated(yaml_str)
        if data is not None:
            logger.info("Truncation recovery succeeded")
            return data
        logger.error("YAML parse failed even after recovery.\nRaw text:\n%s", yaml_str[:500])
        raise


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


def artifact_to_yaml_str(artifact: dict) -> str:
    """Serialize artifact dict back to YAML string."""
    return yaml.dump(artifact, allow_unicode=True, sort_keys=False)
