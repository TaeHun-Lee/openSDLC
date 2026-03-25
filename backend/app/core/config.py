"""Configuration for OpenSDLC backend.

Path constants are resolved once at import time (they never change).
Runtime values (LLM provider, API keys, etc.) are exposed as getter
functions so that ``monkeypatch.setenv()`` in tests is respected.
Module-level constants are kept for backward compatibility but may
reflect stale values in test sessions — prefer the getter functions.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Static path constants (resolved once, never change) ──────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

ENGINE_DIR = PROJECT_ROOT / "core" / "open-sdlc-engine"
CONSTITUTION_DIR = PROJECT_ROOT / "core" / "open-sdlc-constitution"
PROMPTS_DIR = ENGINE_DIR / "prompts" / "agent"
TEMPLATES_DIR = ENGINE_DIR / "templates" / "artifacts"

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PIPELINES_DIR = BACKEND_DIR / "pipelines"
AGENT_OVERRIDES_DIR = BACKEND_DIR / "agent-config-overrides"
MANDATES_DIR = BACKEND_DIR / "app" / "core" / "prompts" / "mandates"


# ── Getter functions (read os.environ at call time) ──────────────────

_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "google": "gemini-2.5-flash",
    "openai": "gpt-4o",
}


def get_llm_provider() -> str:
    return os.environ.get("OPENSDLC_LLM_PROVIDER", "google")


def get_model() -> str:
    provider = get_llm_provider()
    return os.environ.get("OPENSDLC_MODEL", _DEFAULT_MODELS.get(provider, "claude-sonnet-4-6"))


def get_anthropic_api_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "")


def get_google_api_key() -> str:
    return os.environ.get("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY_FILE", ""))


def get_openai_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "")


def get_max_iterations() -> int:
    return int(os.environ.get("OPENSDLC_MAX_ITERATIONS", "3"))


def get_llm_max_retries() -> int:
    return int(os.environ.get("OPENSDLC_LLM_MAX_RETRIES", "2"))


def get_log_level() -> str:
    return os.environ.get("OPENSDLC_LOG_LEVEL", "INFO")


def get_log_llm_io() -> bool:
    return os.environ.get("OPENSDLC_LOG_LLM_IO", "true").lower() == "true"


def get_data_dir() -> Path:
    return Path(os.environ.get("OPENSDLC_DATA_DIR", str(BACKEND_DIR / "data")))


def get_database_path() -> Path:
    return get_data_dir() / "opensdlc.db"


def get_runs_dir() -> Path:
    return get_data_dir() / "runs"


def get_cors_origins() -> list[str]:
    return [
        o.strip()
        for o in os.environ.get("OPENSDLC_CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]


def get_api_key() -> str:
    return os.environ.get("OPENSDLC_API_KEY", "")
