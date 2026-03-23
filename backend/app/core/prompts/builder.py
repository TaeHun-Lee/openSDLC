"""Assemble final system prompts for each agent.

All assembly is config-driven — no agent-specific if/elif branches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.prompts.loader import (
    load_agent_prompt,
    load_common_prompt,
    load_constitution_sections,
    load_mandate,
    load_template,
)

if TYPE_CHECKING:
    from app.core.registry.models import AgentConfig, StepDefinition

_SEPARATOR = "\n\n" + "=" * 60 + "\n\n"


def build_system_prompt(
    agent_config: AgentConfig,
    step: StepDefinition | None = None,
) -> str:
    """Build system prompt for ANY agent from its config."""
    parts: list[str] = []

    # 1. Base prompts
    parts.append("# OpenSDLC Common Rules")
    parts.append(load_common_prompt())
    parts.append(_SEPARATOR)

    parts.append(f"# {agent_config.agent_id} Role & Instructions")
    parts.append(load_agent_prompt(agent_config.agent_id))
    parts.append(_SEPARATOR)

    # 1b. Persona
    persona = agent_config.persona
    if persona.mission or persona.tone or persona.behavioral_rules:
        persona_lines = [f"# {agent_config.agent_id} Persona"]
        if persona.codename:
            persona_lines.append(f"Codename: {persona.codename}")
        if persona.mission:
            persona_lines.append(f"Mission: {persona.mission}")
        if persona.tone:
            persona_lines.append(f"Tone: {persona.tone}")
        if persona.strengths:
            persona_lines.append("Strengths: " + ", ".join(persona.strengths))
        if persona.behavioral_rules:
            persona_lines.append("\nBehavioral Rules:")
            for rule in persona.behavioral_rules:
                persona_lines.append(f"- {rule}")
        parts.append("\n".join(persona_lines))
        parts.append(_SEPARATOR)

    # 2. Output templates
    output_templates = _resolve_output_templates(agent_config, step)
    for tmpl_name in output_templates:
        parts.append(f"# {tmpl_name} Template (MANDATORY REFERENCE)")
        parts.append(
            "You MUST produce output that strictly matches this template schema:\n"
        )
        parts.append(load_template(tmpl_name))
        parts.append(_SEPARATOR)

    # 3. Reference templates
    for ref_tmpl in agent_config.reference_templates:
        parts.append(f"# {ref_tmpl} Template (Schema Reference for Validation)")
        parts.append(
            f"Use this to verify schema compliance of {ref_tmpl} artifacts:\n"
        )
        parts.append(load_template(ref_tmpl))
        parts.append(_SEPARATOR)

    # 4. Extra templates from step definition
    if step and step.extra_templates:
        for extra in step.extra_templates:
            parts.append(f"# {extra} Template (Additional Reference)")
            parts.append(load_template(extra))
            parts.append(_SEPARATOR)

    # 5. Constitution
    parts.append("# OpenSDLC Constitution (Governance Principles)")
    sections = tuple(agent_config.constitution_sections)
    parts.append(load_constitution_sections(sections))

    # 6. Mandate files (agent config + step-level overrides)
    for mandate_filename in agent_config.mandate_files:
        parts.append(_SEPARATOR)
        parts.append(load_mandate(mandate_filename))

    if step and step.extra_mandate_files:
        for mandate_filename in step.extra_mandate_files:
            parts.append(_SEPARATOR)
            parts.append(load_mandate(mandate_filename))

    return "\n".join(parts)


def _resolve_output_templates(
    agent_config: AgentConfig,
    step: StepDefinition | None,
) -> list[str]:
    """Determine which output templates an agent should reference."""
    templates = [o for o in agent_config.primary_outputs if o.endswith("Artifact")]

    if step and step.mode and len(templates) > 1:
        if step.mode == "design":
            return [t for t in templates if "Design" in t] or templates[:1]
        elif step.mode == "execution":
            return [t for t in templates if "Report" in t] or templates[-1:]

    return templates
