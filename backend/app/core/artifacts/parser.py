"""Parse and extract YAML artifacts from LLM responses."""

import re
import logging
import yaml

logger = logging.getLogger(__name__)


def split_narrative_and_yaml(response_text: str) -> tuple[str, str]:
    """Split LLM response into (narrative_text, yaml_artifact)."""
    fence_match = re.search(
        r"```(?:yaml)?\s*\n(.*?)```",
        response_text,
        re.DOTALL,
    )
    if fence_match:
        yaml_part = fence_match.group(1).strip()
        narrative = response_text[:fence_match.start()].strip()
        after = response_text[fence_match.end():].strip()
        if after:
            narrative = f"{narrative}\n{after}".strip() if narrative else after
        yaml_part = _strip_extra_documents(yaml_part)
        return narrative, yaml_part

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
        logger.warning("YAML parse error: %s — attempting truncation recovery", exc)
        data = _try_parse_truncated(yaml_str)
        if data is not None:
            logger.info("Truncation recovery succeeded")
            return data
        logger.error("YAML parse failed even after recovery.\nRaw text:\n%s", yaml_str[:500])
        raise


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
