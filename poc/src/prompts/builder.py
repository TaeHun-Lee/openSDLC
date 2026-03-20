"""Assemble final system prompts for each agent.

Provides a generic build_system_prompt() that works for any agent
based on its AgentConfig and optional StepDefinition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompts.loader import (
    load_agent_prompt,
    load_common_prompt,
    load_template,
    load_constitution_excerpt,
)

if TYPE_CHECKING:
    from registry.models import AgentConfig, StepDefinition

_SEPARATOR = "\n\n" + "=" * 60 + "\n\n"

# Agent → artifact template names for their primary outputs
_OUTPUT_TEMPLATE_MAP: dict[str, list[str]] = {
    "ReqAgent": ["UseCaseModelArtifact"],
    "ValidatorAgent": ["ValidationReportArtifact"],
    "CodeAgent": ["ImplementationArtifact"],
    "TestAgent": ["TestDesignArtifact", "TestReportArtifact"],
    "CoordAgent": ["FeedbackArtifact"],
    "PMAgent": [],
}

# Templates ValidatorAgent needs as schema reference for validation
_VALIDATOR_REFERENCE_TEMPLATES: list[str] = [
    "UseCaseModelArtifact",
    "TestDesignArtifact",
    "ImplementationArtifact",
    "TestReportArtifact",
    "FeedbackArtifact",
]

_CODE_FILE_MANDATE = """# CODE FILE OUTPUT MANDATE
In addition to the standard ImplementationArtifact fields, you MUST include a `code_files` field.
This field contains the COMPLETE, EXECUTABLE source code for every file you create or modify.

Format:
```
code_files:
  - path: "src/main.py"
    language: "python"
    content: |
      #!/usr/bin/env python3
      \"\"\"Main entry point.\"\"\"

      def main():
          print("Hello, World!")

      if __name__ == "__main__":
          main()

  - path: "src/utils.py"
    language: "python"
    content: |
      def helper():
          return 42
```

Rules:
1. Every file listed in `files_changed` MUST have a corresponding entry in `code_files`.
2. Each `content` field must contain the COMPLETE file — no placeholders, no "..." ellipsis, no "# TODO" stubs.
3. The code must be immediately executable with the command in `runtime_info.entrypoint`.
4. Use `|` (literal block scalar) for the `content` field to preserve formatting.
5. File paths must be relative (e.g., "src/app.py", not "/absolute/path/app.py").
6. Include ALL necessary files: entry points, modules, config files, requirements.txt, etc.
7. Do not omit imports, type hints, or error handling for brevity."""

_ADVERSARIAL_MANDATE = """# ADVERSARIAL VALIDATION MANDATE
You are an independent auditor. Before issuing any verdict:
1. List at least 3 potential failure candidates (specific issues you looked for).
2. For each candidate, state whether it is a BLOCKER or NOT.
3. Only issue `pass` if ZERO blockers remain after this analysis.
4. Treat the following as automatic blockers (must fail):
   - Schema non-compliance (missing required fields)
   - Acceptance criteria that are not independently testable
   - Use cases that bundle multiple unrelated user flows
   - Missing traceability (source_artifact_ids empty when upstream exists)
   - Ambiguous or unverifiable acceptance criteria
5. Record your failure candidate analysis in the `checks` field before finalizing."""


# ---------------------------------------------------------------------------
# Generic builder (new)
# ---------------------------------------------------------------------------

def build_system_prompt(
    agent_config: AgentConfig,
    step: StepDefinition | None = None,
) -> str:
    """Build system prompt for ANY agent from its config.

    Args:
        agent_config: The agent's loaded configuration.
        step: Optional step definition for mode-specific or extra template handling.
    """
    agent_id = agent_config.agent_id
    parts: list[str] = []

    # 1. Common rules
    parts.append("# OpenSDLC Common Rules")
    parts.append(load_common_prompt())
    parts.append(_SEPARATOR)

    # 2. Agent-specific prompt
    parts.append(f"# {agent_id} Role & Instructions")
    parts.append(load_agent_prompt(agent_id))
    parts.append(_SEPARATOR)

    # 3. Output templates (mandatory reference for the agent's primary outputs)
    output_templates = _resolve_output_templates(agent_id, step)
    for tmpl_name in output_templates:
        parts.append(f"# {tmpl_name} Template (MANDATORY REFERENCE)")
        parts.append(
            "You MUST produce output that strictly matches this template schema:\n"
        )
        parts.append(load_template(tmpl_name))
        parts.append(_SEPARATOR)

    # 4. ValidatorAgent: all artifact templates as reference + adversarial mandate
    if agent_id == "ValidatorAgent":
        for ref_tmpl in _VALIDATOR_REFERENCE_TEMPLATES:
            parts.append(f"# {ref_tmpl} Template (Schema Reference for Validation)")
            parts.append(
                f"Use this to verify schema compliance of {ref_tmpl} artifacts:\n"
            )
            parts.append(load_template(ref_tmpl))
            parts.append(_SEPARATOR)

    # 5. Extra templates from step definition
    if step and step.extra_templates:
        for extra in step.extra_templates:
            parts.append(f"# {extra} Template (Additional Reference)")
            parts.append(load_template(extra))
            parts.append(_SEPARATOR)

    # 6. Constitution
    parts.append("# OpenSDLC Constitution (Governance Principles)")
    parts.append(load_constitution_excerpt())

    # 7. Adversarial mandate for ValidatorAgent
    if agent_id == "ValidatorAgent":
        parts.append(_SEPARATOR)
        parts.append(_ADVERSARIAL_MANDATE)

    # 8. Code file mandate for CodeAgent
    if agent_id == "CodeAgent":
        parts.append(_SEPARATOR)
        parts.append(_CODE_FILE_MANDATE)

    return "\n".join(parts)


def _resolve_output_templates(
    agent_id: str,
    step: StepDefinition | None,
) -> list[str]:
    """Determine which output templates an agent should reference."""
    templates = _OUTPUT_TEMPLATE_MAP.get(agent_id, [])

    # TestAgent dual mode: filter by mode
    if agent_id == "TestAgent" and step and step.mode:
        if step.mode == "design":
            return ["TestDesignArtifact"]
        elif step.mode == "execution":
            return ["TestReportArtifact"]

    return templates
