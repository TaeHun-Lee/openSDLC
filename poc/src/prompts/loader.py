"""Load prompt and template files from the core/open-sdlc-engine directory."""

from pathlib import Path
from functools import lru_cache

from config import PROMPTS_DIR, TEMPLATES_DIR, CONSTITUTION_DIR, ENGINE_DIR

MANDATES_DIR = Path(__file__).parent / "mandates"


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
def load_constitution_sections(filenames: tuple[str, ...] = ()) -> str:
    """Load selected constitution sections.

    Args:
        filenames: Tuple of constitution filenames to load.
                   Empty tuple loads all files (backward compat).
    """
    excerpts: list[str] = []
    if filenames:
        for fname in filenames:
            path = CONSTITUTION_DIR / fname
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()[:60]
            excerpts.append(f"## {fname}\n" + "\n".join(lines))
    else:
        for path in sorted(CONSTITUTION_DIR.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()[:60]
            excerpts.append(f"## {path.name}\n" + "\n".join(lines))
    return "\n\n---\n\n".join(excerpts)


@lru_cache(maxsize=None)
def load_mandate(filename: str) -> str:
    """Load a mandate file from prompts/mandates/."""
    path = MANDATES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Mandate not found: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def load_core_concepts() -> str:
    """Load core-concept.md for context."""
    path = ENGINE_DIR / "core-concepts" / "core-concept.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""
