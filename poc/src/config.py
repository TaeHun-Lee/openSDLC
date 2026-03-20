"""Configuration for OpenSDLC PoC."""

import os
from pathlib import Path

# Project root (poc/../)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Methodology directories (read-only)
ENGINE_DIR = PROJECT_ROOT / "open-sdlc-engine"
CONSTITUTION_DIR = PROJECT_ROOT / "open-sdlc-constitution"
PROMPTS_DIR = ENGINE_DIR / "prompts" / "agent"
TEMPLATES_DIR = ENGINE_DIR / "templates" / "artifacts"

# LLM Provider selection: "anthropic" | "google" | "openai"
LLM_PROVIDER = os.environ.get("OPENSDLC_LLM_PROVIDER", "google")

# Provider API keys
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyBJ95EWbofsMoXa1lD1PNJ74WCw8aro3sk")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Default model per provider (overridden by OPENSDLC_MODEL env var)
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
