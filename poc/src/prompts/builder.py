"""Assemble final system prompts for each agent.

Provides a generic build_system_prompt() that works for any agent
based on its AgentConfig and optional StepDefinition.
All assembly is config-driven — no agent-specific if/elif branches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompts.loader import (
    load_agent_prompt,
    load_common_prompt,
    load_constitution_sections,
    load_mandate,
    load_template,
)

if TYPE_CHECKING:
    from registry.models import AgentConfig, StepDefinition

_SEPARATOR = "\n\n" + "=" * 60 + "\n\n"


def build_system_prompt(
    agent_config: AgentConfig,
    step: StepDefinition | None = None,
) -> str:
    """Build system prompt for ANY agent from its config.

    Assembly order:
      1. base_prompt_files → AgentCommon + agent-specific prompt
      2. primary_outputs → output templates (TestAgent filtered by step.mode)
      3. reference_templates → schema references for validation
      4. extra_templates from step definition
      5. constitution_sections → selective constitution loading
      6. mandate_files → special directives (adversarial, code_file, etc.)
    """
    parts: list[str] = []

    # 1. Base prompts (AgentCommon + agent-specific)
    parts.append("# OpenSDLC Common Rules")
    parts.append(load_common_prompt())
    parts.append(_SEPARATOR)

    parts.append(f"# {agent_config.agent_id} Role & Instructions")
    parts.append(load_agent_prompt(agent_config.agent_id))
    parts.append(_SEPARATOR)

    # 1b. Persona (tone, mission, behavioral rules from config)
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

    # 2. Output templates from primary_outputs
    output_templates = _resolve_output_templates(agent_config, step)
    for tmpl_name in output_templates:
        parts.append(f"# {tmpl_name} Template (MANDATORY REFERENCE)")
        parts.append(
            "You MUST produce output that strictly matches this template schema:\n"
        )
        parts.append(load_template(tmpl_name))
        parts.append(_SEPARATOR)

    # 3. Reference templates (e.g. ValidatorAgent's schema references)
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

    # 5. Constitution (selective or full)
    parts.append("# OpenSDLC Constitution (Governance Principles)")
    sections = tuple(agent_config.constitution_sections)
    parts.append(load_constitution_sections(sections))

    # 6. Mandate files (adversarial, code_file, etc.)
    for mandate_filename in agent_config.mandate_files:
        parts.append(_SEPARATOR)
        parts.append(load_mandate(mandate_filename))

    return "\n".join(parts)


def _resolve_output_templates(
    agent_config: AgentConfig,
    step: StepDefinition | None,
) -> list[str]:
    """Determine which output templates an agent should reference.

    Uses agent_config.primary_outputs, filtering artifact-type entries.
    For TestAgent with dual mode, filters by step.mode.
    """
    # Filter primary_outputs to only known artifact template names (ending with "Artifact")
    templates = [o for o in agent_config.primary_outputs if o.endswith("Artifact")]

    # TestAgent dual mode: filter by step.mode
    if step and step.mode and len(templates) > 1:
        if step.mode == "design":
            return [t for t in templates if "Design" in t] or templates[:1]
        elif step.mode == "execution":
            return [t for t in templates if "Report" in t] or templates[-1:]

    return templates
