"""Scan existing workspace directories for agent context."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Extensions commonly used in code projects
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".yaml", ".yml",
    ".md", ".txt", ".sh", ".sql", ".env", ".toml", ".ini", ".cfg",
}

# Directories to ignore
IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", "dist", "build", "venv", ".venv",
    ".idea", ".vscode", "artifacts", "runs", ".gemini", ".claude",
}


def scan_workspace(workspace_dir: str | Path) -> dict[str, str]:
    """Scan the workspace directory and return a dict of {rel_path: content}.

    Skips common binary/ignored directories and limits file size to keep
    the LLM context manageable.
    """
    workspace = Path(workspace_dir)
    if not workspace.exists() or not workspace.is_dir():
        logger.warning("Workspace directory not found or not a directory: %s", workspace_dir)
        return {}

    context: dict[str, str] = {}
    try:
        # Resolve to absolute path for reliable prefix check
        workspace_abs = workspace.resolve()
        
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue

            # Skip ignored directories in the path
            if any(part in IGNORE_DIRS for part in path.parts):
                continue

            # Only read text files based on extension
            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue

            # Limit individual file size (e.g., 50KB) to avoid context explosion
            try:
                if path.stat().st_size > 50 * 1024:
                    logger.debug("Skipping large file: %s", path)
                    continue

                rel_path = str(path.relative_to(workspace_abs))
                content = path.read_text(encoding="utf-8", errors="replace")
                context[rel_path] = content
            except (OSError, ValueError) as exc:
                logger.error("Failed to process file '%s': %s", path, exc)

    except Exception as exc:
        logger.error("Error scanning workspace '%s': %s", workspace_dir, exc)

    logger.info("Scanned workspace '%s': found %d files", workspace_dir, len(context))
    return context
