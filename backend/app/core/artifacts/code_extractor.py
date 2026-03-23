"""Extract executable code files from ImplementationArtifact YAML."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def extract_code_files(impl_artifact_yaml: str) -> list[dict[str, str]]:
    """Parse code_files from an ImplementationArtifact YAML string."""
    try:
        data = yaml.safe_load(impl_artifact_yaml)
    except yaml.YAMLError as exc:
        logger.error("Failed to parse ImplementationArtifact YAML: %s", exc)
        return []

    if not isinstance(data, dict):
        logger.error("ImplementationArtifact is not a dict")
        return []

    code_files = data.get("code_files")
    if not code_files:
        logger.warning("No 'code_files' field in ImplementationArtifact")
        return []

    if not isinstance(code_files, list):
        logger.error("'code_files' is not a list: %s", type(code_files))
        return []

    result: list[dict[str, str]] = []
    for entry in code_files:
        if not isinstance(entry, dict):
            continue
        file_path = entry.get("path", "")
        content = entry.get("content", "")
        language = entry.get("language", "")
        if not file_path or not content:
            continue
        result.append({"path": file_path, "language": language, "content": content})

    return result


def _strip_workspace_prefix(rel_path: str) -> str:
    """Strip leading 'workspace/' prefix."""
    parts = rel_path.replace("\\", "/").split("/")
    if parts and parts[0].lower() == "workspace":
        return "/".join(parts[1:])
    return rel_path


def write_code_files(
    impl_artifact_yaml: str,
    workspace_dir: str | Path,
) -> list[Path]:
    """Extract code files from ImplementationArtifact and write them to disk."""
    workspace = Path(workspace_dir)
    code_files = extract_code_files(impl_artifact_yaml)

    if not code_files:
        return []

    written: list[Path] = []
    for entry in code_files:
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


def get_runtime_info(impl_artifact_yaml: str) -> dict[str, str]:
    """Extract runtime_info (entrypoint, test_url) from ImplementationArtifact."""
    try:
        data = yaml.safe_load(impl_artifact_yaml)
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data.get("runtime_info", {}) or {}
