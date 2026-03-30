"""Extract and write code files from pipeline agent output."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _strip_workspace_prefix(rel_path: str) -> str:
    """Strip leading 'workspace/' prefix."""
    parts = rel_path.replace("\\", "/").split("/")
    if parts and parts[0].lower() == "workspace":
        return "/".join(parts[1:])
    return rel_path


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


def get_runtime_info(impl_artifact_yaml: str) -> dict[str, str]:
    """Extract runtime_info (entrypoint, test_url) from ImplementationArtifact."""
    import yaml

    try:
        data = yaml.safe_load(impl_artifact_yaml)
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data.get("runtime_info", {}) or {}
