"""Agent registry — loads and provides access to all agent configurations."""

import logging
from functools import lru_cache
from pathlib import Path

import yaml

from registry.models import AgentConfig, AgentPersona

logger = logging.getLogger(__name__)

_AGENT_CONFIGS_DIR = (
    Path(__file__).parent.parent.parent.parent / "open-sdlc-engine" / "agent-configs"
)


@lru_cache(maxsize=1)
def load_all_agents() -> dict[str, AgentConfig]:
    """Load all agent configs from agent-configs/*.config.yaml, keyed by agent_id."""
    agents: dict[str, AgentConfig] = {}

    if not _AGENT_CONFIGS_DIR.is_dir():
        logger.warning("Agent configs directory not found: %s", _AGENT_CONFIGS_DIR)
        return agents

    for config_file in sorted(_AGENT_CONFIGS_DIR.glob("*.config.yaml")):
        try:
            raw = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                logger.warning("Skipping %s — not a dict", config_file.name)
                continue

            # Parse persona separately to flatten behavioral_rules
            persona_raw = raw.pop("persona", {})
            persona = AgentPersona(**persona_raw)

            # Remove fields not in AgentConfig
            raw.pop("reporting_contract", None)
            raw.pop("interaction_policy", None)

            config = AgentConfig(persona=persona, **raw)
            agents[config.agent_id] = config
            logger.debug("Loaded agent config: %s", config.agent_id)

        except Exception as exc:
            logger.error("Failed to load %s: %s", config_file.name, exc)

    logger.info("Loaded %d agent configs: %s", len(agents), list(agents.keys()))
    return agents


def get_agent(agent_id: str) -> AgentConfig:
    """Get a single agent config by ID. Raises KeyError if not found."""
    agents = load_all_agents()
    if agent_id not in agents:
        raise KeyError(
            f"Unknown agent: {agent_id!r}. Available: {list(agents.keys())}"
        )
    return agents[agent_id]


def list_agents() -> list[str]:
    """Return all registered agent IDs."""
    return list(load_all_agents().keys())
