"""Extract executable code files from ImplementationArtifact YAML.

Parses the `code_files` field and writes each file to disk under the
specified workspace directory.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def extract_code_files(impl_artifact_yaml: str) -> list[dict[str, str]]:
    """Parse code_files from an ImplementationArtifact YAML string.

    Returns a list of dicts with keys: path, language, content.
    Returns empty list if code_files field is missing or unparseable.
    """
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
        logger.warning(
            "No 'code_files' field in ImplementationArtifact — "
            "CodeAgent may not have produced executable code."
        )
        return []

    if not isinstance(code_files, list):
        logger.error("'code_files' is not a list: %s", type(code_files))
        return []

    result: list[dict[str, str]] = []
    for entry in code_files:
        if not isinstance(entry, dict):
            logger.warning("Skipping non-dict code_files entry: %s", entry)
            continue

        file_path = entry.get("path", "")
        content = entry.get("content", "")
        language = entry.get("language", "")

        if not file_path:
            logger.warning("Skipping code_files entry with empty path")
            continue

        if not content:
            logger.warning("Skipping code_files entry with empty content: %s", file_path)
            continue

        result.append({
            "path": file_path,
            "language": language,
            "content": content,
        })

    return result


def write_code_files(
    impl_artifact_yaml: str,
    workspace_dir: str | Path,
) -> list[Path]:
    """Extract code files from ImplementationArtifact and write them to disk.

    Args:
        impl_artifact_yaml: The raw YAML string of the ImplementationArtifact.
        workspace_dir: Root directory to write files under.

    Returns:
        List of absolute paths of files written.
    """
    workspace = Path(workspace_dir)
    code_files = extract_code_files(impl_artifact_yaml)

    if not code_files:
        logger.warning("No code files to write.")
        return []

    written: list[Path] = []
    for entry in code_files:
        rel_path = entry["path"]
        content = entry["content"]

        # Security: prevent path traversal
        try:
            resolved = (workspace / rel_path).resolve()
            if not str(resolved).startswith(str(workspace.resolve())):
                logger.error(
                    "Path traversal detected, skipping: %s", rel_path
                )
                continue
        except (ValueError, OSError) as exc:
            logger.error("Invalid path '%s': %s", rel_path, exc)
            continue

        # Create parent directories
        resolved.parent.mkdir(parents=True, exist_ok=True)

        # Write file
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
