"""Load prompt and template files from the open-sdlc-engine directory."""

from pathlib import Path
from functools import lru_cache

from config import PROMPTS_DIR, TEMPLATES_DIR, CONSTITUTION_DIR, ENGINE_DIR


@lru_cache(maxsize=None)
def load_agent_prompt(agent_name: str) -> str:
    """Load agent system prompt text (e.g., 'ReqAgent', 'ValidatorAgent')."""
    path = PROMPTS_DIR / f"{agent_name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Agent prompt not found: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def load_common_prompt() -> str:
    """Load AgentCommon.txt shared rules."""
    return load_agent_prompt("AgentCommon")


@lru_cache(maxsize=None)
def load_template(artifact_name: str) -> str:
    """Load artifact YAML template (e.g., 'UseCaseModelArtifact')."""
    path = TEMPLATES_DIR / f"{artifact_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def load_constitution_excerpt() -> str:
    """Load core governance principles from constitution files."""
    excerpts: list[str] = []
    for fname in sorted(CONSTITUTION_DIR.glob("*.md")):
        text = fname.read_text(encoding="utf-8")
        # Take first 60 lines of each constitution file as key principles
        lines = text.splitlines()[:60]
        excerpts.append(f"## {fname.name}\n" + "\n".join(lines))
    return "\n\n---\n\n".join(excerpts)


@lru_cache(maxsize=None)
def load_core_concepts() -> str:
    """Load core-concept.md for context."""
    path = ENGINE_DIR / "core-concepts" / "core-concept.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""
