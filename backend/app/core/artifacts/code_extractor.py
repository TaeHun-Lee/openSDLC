"""Extract and write code files from pipeline agent output."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def apply_search_replace(original_text: str, patch_text: str) -> str:
    """Apply SEARCH/REPLACE blocks to original text.
    
    Args:
        original_text: Existing file content.
        patch_text: Text containing one or more SEARCH/REPLACE blocks.
        
    Returns:
        Updated text.
        
    Raises:
        ValueError: If a SEARCH block is not found or is ambiguous.
    """
    # Regex to find all SEARCH/REPLACE blocks
    pattern = re.compile(
        r"<<<< SEARCH\n(.*?)\n====\n(.*?)\n>>>> REPLACE",
        re.DOTALL
    )
    
    matches = pattern.findall(patch_text)
    if not matches:
        # If no markers found, treat as full content (fallback)
        return patch_text

    current_text = original_text
    for search_block, replace_block in matches:
        # Check for exact match (including whitespace)
        if search_block not in current_text:
            raise ValueError(f"SEARCH block not found in original file:\n{search_block}")
        
        # Check for ambiguity (occurs more than once)
        if current_text.count(search_block) > 1:
            raise ValueError(f"SEARCH block is ambiguous (found multiple times):\n{search_block}")
            
        current_text = current_text.replace(search_block, replace_block)
        
    return current_text


def parse_code_context(context_text: str) -> dict[str, str]:
    """Parse a formatted code context string back into a dict of {path: content}.
    
    Expected format:
    <!-- FILE: path -->
    ```language
    content
    ```
    """
    results = {}
    pattern = re.compile(
        r"<!--\s*FILE:\s*(.+?)\s*-->\s*\n"
        r"```[^\n]*?\s*\n"
        r"(.*?)"
        r"\n```",
        re.DOTALL
    )
    for match in pattern.finditer(context_text):
        path = match.group(1).strip().strip("\"'")
        content = match.group(2)
        results[path] = content
    return results


def format_code_context(code_map: dict[str, str]) -> str:
    """Format a dict of {path: content} into a single string for LLM context."""
    parts = []
    for path, content in sorted(code_map.items()):
        # Determine language from extension for better markdown rendering
        ext = Path(path).suffix.lstrip(".")
        lang = ext if ext else "text"
        parts.append(
            f"<!-- FILE: {path} -->\n"
            f"```{lang}\n{content}\n```"
        )
    return "\n\n".join(parts)


def merge_code_blocks(
    previous_context: str,
    new_blocks: list[dict[str, str]]
) -> str:
    """Merge new code blocks (possibly Search-Replace) into previous full context.
    
    Returns a formatted string containing the full updated code.
    """
    code_map = parse_code_context(previous_context)
    
    for block in new_blocks:
        path = block["path"]
        content = block["content"]
        
        if "<<<< SEARCH" in content and ">>>> REPLACE" in content:
            if path in code_map:
                try:
                    code_map[path] = apply_search_replace(code_map[path], content)
                except ValueError as exc:
                    logger.error("Failed to merge code block for %s: %s", path, exc)
                    # Keep previous version on failure
            else:
                logger.warning("Search-Replace block for new file %s. Using content as-is.", path)
                code_map[path] = content
        else:
            # Full content update
            code_map[path] = content
            
    return format_code_context(code_map)


def _strip_workspace_prefix(rel_path: str) -> str:
    """Strip leading 'workspace/' prefix."""
    parts = rel_path.replace("\\", "/").split("/")
    if parts and parts[0].lower() == "workspace":
        return "/".join(parts[1:])
    return rel_path


def normalize_code_path(
    raw_path: str,
    workspace_root_name: str | None = None,
    workspace_mode: str = "internal_run_workspace",
) -> str:
    """Normalize a model-emitted code path into workspace-root-relative form."""
    normalized = raw_path.replace("\\", "/").strip()
    normalized = _strip_workspace_prefix(normalized).lstrip("/")
    if not normalized:
        raise ValueError("Empty code path")

    if os.path.isabs(raw_path):
        raise ValueError(f"Absolute paths are not allowed: {raw_path}")

    if workspace_mode == "external_project_root" and workspace_root_name:
        prefix = f"{workspace_root_name}/"
        if normalized.startswith(prefix):
            logger.warning(
                "Code path includes workspace root slug prefix '%s'. Normalized to '%s'.",
                prefix,
                normalized[len(prefix):],
            )
            normalized = normalized[len(prefix):]

    candidate = Path(normalized)
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"Path traversal is not allowed: {raw_path}")
    if normalized in ("", "."):
        raise ValueError(f"Invalid normalized path: {raw_path}")
    return normalized


def write_code_blocks(
    code_blocks: list[dict[str, str]],
    workspace_dir: str | Path,
    workspace_root_name: str | None = None,
    workspace_mode: str = "internal_run_workspace",
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
        try:
            rel_path = normalize_code_path(
                entry["path"],
                workspace_root_name=workspace_root_name,
                workspace_mode=workspace_mode,
            )
        except ValueError as exc:
            logger.error("Invalid code path '%s': %s", entry["path"], exc)
            continue
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
        
        # Check for Search-Replace protocol
        if "<<<< SEARCH" in content and ">>>> REPLACE" in content:
            if resolved.exists():
                try:
                    original_content = resolved.read_text(encoding="utf-8")
                    content = apply_search_replace(original_content, content)
                    logger.info("Search-Replace applied to %s", rel_path)
                except ValueError as exc:
                    logger.error("Failed to apply Search-Replace to %s: %s", rel_path, exc)
                    # For now, we skip the file on merge failure to prevent corruption.
                    continue
            else:
                logger.warning("Search-Replace marker found but file %s does not exist. Using content as-is (full write).", rel_path)

        # Backup existing file before overwriting
        if resolved.exists():
            import time
            timestamp = int(time.time())
            backup_path = resolved.with_suffix(f"{resolved.suffix}.bak.{timestamp}")
            try:
                import shutil
                shutil.copy2(resolved, backup_path)
                logger.info("Backup created: %s", backup_path)
            except Exception as exc:
                logger.error("Failed to create backup for %s: %s", resolved, exc)

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
