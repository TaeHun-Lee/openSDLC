"""Configuration for OpenSDLC backend."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root: openSDLC/ (backend/../)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Methodology directories (read-only, from core/ submodule)
ENGINE_DIR = PROJECT_ROOT / "core" / "open-sdlc-engine"
CONSTITUTION_DIR = PROJECT_ROOT / "core" / "open-sdlc-constitution"
PROMPTS_DIR = ENGINE_DIR / "prompts" / "agent"
TEMPLATES_DIR = ENGINE_DIR / "templates" / "artifacts"

# Backend-local directories
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PIPELINES_DIR = BACKEND_DIR / "pipelines"
AGENT_OVERRIDES_DIR = BACKEND_DIR / "agent-config-overrides"
MANDATES_DIR = BACKEND_DIR / "app" / "core" / "prompts" / "mandates"

# LLM Provider selection: "anthropic" | "google" | "openai"
LLM_PROVIDER = os.environ.get("OPENSDLC_LLM_PROVIDER", "google")

# Provider API keys
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY_FILE", ""))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Default model per provider
_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "google": "gemini-2.5-flash",
    "openai": "gpt-4o",
}
MODEL = os.environ.get("OPENSDLC_MODEL", _DEFAULT_MODELS.get(LLM_PROVIDER, "claude-sonnet-4-6"))

# Pipeline settings
MAX_ITERATIONS = int(os.environ.get("OPENSDLC_MAX_ITERATIONS", "3"))

# LLM quality guard
LLM_MAX_RETRIES = int(os.environ.get("OPENSDLC_LLM_MAX_RETRIES", "2"))

# Logging
LOG_LEVEL = os.environ.get("OPENSDLC_LOG_LEVEL", "INFO")
LOG_LLM_IO = os.environ.get("OPENSDLC_LOG_LLM_IO", "true").lower() == "true"
