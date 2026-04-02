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
    load_report_template,
    load_template,
)

if TYPE_CHECKING:
    from app.core.registry.models import AgentConfig, StepDefinition

_SEPARATOR = "\n\n" + "=" * 60 + "\n\n"


def _resolve_output_contract(
    agent_config: AgentConfig,
    step: StepDefinition | None,
) -> dict[str, object]:
    """Resolve the runtime output contract for a step."""
    artifact_templates = [o for o in agent_config.primary_outputs if o.endswith("Artifact")]
    report_template = step.report_template if step else None

    if step and step.output_mode:
        output_mode = step.output_mode
    elif artifact_templates:
        output_mode = "yaml_artifact"
    elif step and step.report_template and step.on_next_iteration:
        output_mode = "markdown_report"
    else:
        output_mode = "narrative_only" if agent_config.agent_id == "PMAgent" else "yaml_artifact"

    if step and step.mode and len(artifact_templates) > 1:
        if step.mode == "design":
            artifact_templates = [t for t in artifact_templates if "Design" in t] or artifact_templates[:1]
        elif step.mode == "execution":
            artifact_templates = [t for t in artifact_templates if "Report" in t] or artifact_templates[-1:]

    return {
        "output_mode": output_mode,
        "artifact_templates": artifact_templates,
        "report_template": report_template,
    }


def _apply_output_contract_to_common_prompt(common_prompt: str, output_mode: str) -> str:
    """Override YAML-only language from AgentCommon at runtime."""
    replacements = {
        "- Always produce exactly ONE artifact.": "- Follow the runtime output contract for this step exactly.",
        "- The artifact must follow the defined YAML schema.": "- If this step emits a YAML artifact, it must follow the defined schema.",
        "- Do not wrap the YAML in markdown.": "- Emit output in the format required by the runtime output contract.",
        "- For the final artifact itself, output YAML only.": "- For the final output itself, follow the runtime output contract exactly.",
    }
    for old, new in replacements.items():
        common_prompt = common_prompt.replace(old, new)

    if output_mode == "narrative_only":
        contract = (
            "# Runtime Output Contract\n"
            "This step has output_mode = narrative_only.\n"
            "- Output narrative only.\n"
            "- Do not emit YAML artifact bodies.\n"
            "- Do not wrap structured YAML in markdown fences.\n"
        )
    elif output_mode == "markdown_report":
        contract = (
            "# Runtime Output Contract\n"
            "This step has output_mode = markdown_report.\n"
            "- Output the report body only.\n"
            "- Follow the attached markdown report template.\n"
            "- Do not emit YAML artifact bodies.\n"
        )
    else:
        contract = (
            "# Runtime Output Contract\n"
            "This step has output_mode = yaml_artifact.\n"
            "- Output exactly one YAML artifact body.\n"
            "- Do not include narrative before or after the artifact body.\n"
        )
    return f"{common_prompt}{_SEPARATOR}{contract}"


def build_system_prompt(
    agent_config: AgentConfig,
    step: StepDefinition | None = None,
) -> str:
    """Build system prompt for ANY agent from its config."""
    parts: list[str] = []
    output_contract = _resolve_output_contract(agent_config, step)
    output_mode = str(output_contract["output_mode"])

    # 1. Base prompts
    parts.append("# OpenSDLC Common Rules")
    parts.append(_apply_output_contract_to_common_prompt(load_common_prompt(), output_mode))
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
    output_templates = list(output_contract["artifact_templates"])
    for tmpl_name in output_templates:
        parts.append(f"# {tmpl_name} Template (MANDATORY REFERENCE)")
        parts.append(
            "You MUST produce output that strictly matches this template schema:\n"
        )
        parts.append(load_template(tmpl_name))
        parts.append(_SEPARATOR)

    report_template = output_contract["report_template"]
    if isinstance(report_template, str) and report_template:
        parts.append(f"# {report_template} Report Template (MANDATORY REFERENCE)")
        parts.append("You MUST produce output that strictly matches this report template:\n")
        parts.append(load_report_template(report_template))
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
