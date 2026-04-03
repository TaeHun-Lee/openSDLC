"""Pipeline compiler — validates user input, auto-infers on_fail, serializes to YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.core.config import (
    get_anthropic_api_key,
    get_google_api_key,
    get_llm_provider,
    get_openai_api_key,
)
from app.core.registry.agent_registry import get_agent, load_all_agents
from app.core.registry.models import PipelineDefinition, StepDefinition
from app.models.requests import CreatePipelineRequest, PipelineStepInput
from app.models.responses import (
    ArtifactFlowStep,
    PipelineValidationResult,
    ValidationIssue,
)

_VALID_PROVIDERS = {"anthropic", "google", "openai", "ollama"}

_PROVIDER_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def validate_pipeline_request(
    steps: list[PipelineStepInput],
) -> list[str]:
    """Validate pipeline step inputs. Returns list of error strings (empty = OK)."""
    errors: list[str] = []
    available_agents = set(load_all_agents().keys())

    for i, step in enumerate(steps, start=1):
        pos = f"step {i}"

        # Agent must exist in registry
        if step.agent not in available_agents:
            errors.append(
                f"{pos}: unknown agent '{step.agent}'. "
                f"Available: {sorted(available_agents)}"
            )

        # TestAgent requires mode
        if step.agent == "TestAgent" and step.mode not in ("design", "execution"):
            errors.append(
                f"{pos}: TestAgent requires mode='design' or mode='execution', "
                f"got {step.mode!r}"
            )

        # ValidatorAgent cannot be first step (no on_fail target)
        if step.agent == "ValidatorAgent" and i == 1:
            errors.append(
                f"{pos}: ValidatorAgent cannot be the first step "
                f"(no preceding agent for rework)"
            )

        # ValidatorAgent needs a preceding non-Validator
        if step.agent == "ValidatorAgent" and i > 1:
            has_target = any(
                s.agent != "ValidatorAgent" for s in steps[:i - 1]
            )
            if not has_target:
                errors.append(
                    f"{pos}: ValidatorAgent has no preceding non-Validator agent "
                    f"to use as rework target"
                )

        # Provider must be valid if specified
        if step.provider and step.provider not in _VALID_PROVIDERS:
            errors.append(
                f"{pos}: invalid provider '{step.provider}'. "
                f"Valid: {sorted(_VALID_PROVIDERS)}"
            )

    return errors


def compile_pipeline(request: CreatePipelineRequest) -> PipelineDefinition:
    """Compile user request into a PipelineDefinition with auto-inferred fields.

    Auto-infers:
    - step numbers (1-based from array order)
    - ValidatorAgent on_fail (nearest preceding non-Validator)
    - PMAgent on_next_iteration (if last step + ReqAgent exists)
    """
    compiled_steps: list[StepDefinition] = []

    for i, step_input in enumerate(request.steps):
        step_num = i + 1
        on_fail: str | None = None
        on_next_iteration: str | None = None

        # Auto-infer on_fail for ValidatorAgent
        if step_input.agent == "ValidatorAgent":
            for j in range(i - 1, -1, -1):
                if request.steps[j].agent != "ValidatorAgent":
                    on_fail = request.steps[j].agent
                    break

        # Auto-infer on_next_iteration for PMAgent if it's the last step
        if step_input.agent == "PMAgent" and i == len(request.steps) - 1:
            req_agents = [s for s in request.steps if s.agent == "ReqAgent"]
            if req_agents:
                on_next_iteration = "ReqAgent"

        compiled_steps.append(
            StepDefinition(
                step=step_num,
                agent=step_input.agent,
                model=step_input.model,
                provider=step_input.provider,
                on_fail=on_fail,
                on_next_iteration=on_next_iteration,
                mode=step_input.mode,
                max_tokens=step_input.max_tokens,
            )
        )

    return PipelineDefinition(
        name=request.name,
        description=request.description,
        max_iterations=request.max_iterations,
        max_reworks_per_gate=request.max_reworks_per_gate,
        steps=compiled_steps,
    )


def save_pipeline_yaml(path: Path, pipeline_def: PipelineDefinition) -> None:
    """Serialize PipelineDefinition to a YAML file."""
    data = pipeline_def.model_dump(exclude_none=True)
    # Exclude defaults that match StepDefinition defaults to keep YAML clean
    for step in data.get("steps", []):
        if step.get("max_tokens") == 8192:
            del step["max_tokens"]
        if step.get("min_response_chars") == 1000:
            del step["min_response_chars"]
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_and_merge_update(
    existing_path: Path,
    description: str | None,
    max_iterations: int | None,
    max_reworks_per_gate: int | None,
    steps: list[PipelineStepInput] | None,
) -> CreatePipelineRequest:
    """Load existing pipeline YAML and merge update fields into a CreatePipelineRequest.

    If steps is provided, replaces entire step list (triggers recompilation).
    Otherwise, only metadata fields are updated.
    """
    raw = yaml.safe_load(existing_path.read_text(encoding="utf-8"))
    name = existing_path.stem

    # Merge metadata
    merged_desc = description if description is not None else raw.get("description", "")
    merged_iter = max_iterations if max_iterations is not None else raw.get("max_iterations", 3)
    merged_reworks = (
        max_reworks_per_gate
        if max_reworks_per_gate is not None
        else raw.get("max_reworks_per_gate", 3)
    )

    # Merge steps
    if steps is not None:
        merged_steps = steps
    else:
        # Convert existing YAML steps back to PipelineStepInput
        merged_steps = [
            PipelineStepInput(
                agent=s["agent"],
                model=s.get("model"),
                provider=s.get("provider"),
                mode=s.get("mode"),
                max_tokens=s.get("max_tokens", 8192),
            )
            for s in raw.get("steps", [])
        ]

    return CreatePipelineRequest(
        name=name,
        description=merged_desc,
        max_iterations=merged_iter,
        max_reworks_per_gate=merged_reworks,
        steps=merged_steps,
    )


def _input_satisfied(required_input: str, available: set[str]) -> bool:
    """Check if a required input is satisfied by the available artifacts.

    Agent configs use descriptive input names like "ValidationReportArtifact for UC stage"
    while outputs are base names like "ValidationReportArtifact".  An input is satisfied if:
    1. Exact match exists in available, OR
    2. Any available artifact is a prefix of the input (base type match).
    """
    if not available:
        return False
    if required_input in available:
        return True
    # Fuzzy: "ValidationReportArtifact" satisfies "ValidationReportArtifact for UC stage"
    return any(required_input.startswith(art) for art in available)


def validate_pipeline_runtime(pipeline_def: PipelineDefinition) -> PipelineValidationResult:
    """Validate a pipeline definition against runtime environment and agent configs.

    Checks:
    - Agent existence in registry (error)
    - API key availability for each step's provider (warning)
    - Artifact input/output compatibility between steps (warning)
    - Rework routing reachability — on_fail target in graph (error)
    - Iteration routing — PMAgent presence and on_next_iteration (warning)

    Returns a PipelineValidationResult with errors, warnings, and artifact_flow.
    """
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    artifact_flow: list[ArtifactFlowStep] = []

    available_agents = load_all_agents()
    default_provider = get_llm_provider()

    # Track which artifact types are available at each point in the pipeline.
    # "user request" is always available from PipelineState.user_story.
    available_artifacts: set[str] = {"user request"}
    step_agents: dict[int, str] = {}  # step_num -> agent_id

    for step_def in pipeline_def.steps:
        step_num = step_def.step
        agent_id = step_def.agent
        step_agents[step_num] = agent_id

        # 1. Agent existence
        if agent_id not in available_agents:
            errors.append(ValidationIssue(
                type="unknown_agent",
                step=step_num,
                agent=agent_id,
                message=f"Agent '{agent_id}' not found in registry. "
                        f"Available: {sorted(available_agents.keys())}",
            ))
            artifact_flow.append(ArtifactFlowStep(
                step=step_num, agent=agent_id,
            ))
            continue

        agent_config = available_agents[agent_id]

        # 2. API key check
        provider = step_def.provider or default_provider
        key_fn = {
            "anthropic": get_anthropic_api_key,
            "google": get_google_api_key,
            "openai": get_openai_api_key,
        }.get(provider)
        if key_fn and not key_fn():
            env_var = _PROVIDER_KEY_ENV.get(provider, f"{provider.upper()}_API_KEY")
            warnings.append(ValidationIssue(
                type="api_key_missing",
                step=step_num,
                agent=agent_id,
                provider=provider,
                message=f"{env_var} environment variable is not set",
            ))

        # 3. Artifact flow analysis
        #
        # Agent configs declare primary_inputs listing ALL possible inputs across
        # modes, rework cycles, and iterations.  Most inputs are conditional:
        # - ValidatorAgent lists 6+ artifact types but validates only 1 per step
        # - TestAgent has design/execution modes with disjoint inputs
        # - ReqAgent only needs ValidationReport when reworking
        #
        # Strategy: warn only when NONE of the declared inputs are available,
        # meaning the agent has nothing to work with at this pipeline point.
        # Individual missing inputs are expected for polymorphic agents.
        consumes: list[str] = []
        produces: list[str] = list(agent_config.primary_outputs)
        missing_inputs: list[str] = []

        for inp in agent_config.primary_inputs:
            consumes.append(inp)
            if not _input_satisfied(inp, available_artifacts):
                missing_inputs.append(inp)

        # Warn only if ALL inputs are missing (agent has nothing to work with)
        if missing_inputs and len(missing_inputs) == len(agent_config.primary_inputs):
            warnings.append(ValidationIssue(
                type="input_not_available",
                step=step_num,
                agent=agent_id,
                message=f"Agent '{agent_id}' has no available inputs at this step. "
                        f"Expected: {agent_config.primary_inputs}. "
                        f"Available: {sorted(available_artifacts) or '(none)'}",
            ))

        artifact_flow.append(ArtifactFlowStep(
            step=step_num, agent=agent_id,
            produces=produces, consumes=consumes,
        ))

        available_artifacts.update(produces)

        # 4. Rework routing reachability
        if step_def.on_fail:
            target_exists = any(
                s.agent == step_def.on_fail
                for s in pipeline_def.steps
                if s.step < step_num
            )
            if not target_exists:
                errors.append(ValidationIssue(
                    type="unreachable_rework_target",
                    step=step_num,
                    agent=agent_id,
                    message=f"on_fail target '{step_def.on_fail}' is not a preceding "
                            f"step in the pipeline",
                ))

    # 5. Iteration routing check
    has_pm = any(s.agent == "PMAgent" for s in pipeline_def.steps)
    if pipeline_def.max_iterations > 1 and not has_pm:
        warnings.append(ValidationIssue(
            type="no_pm_agent",
            message="max_iterations > 1 but no PMAgent in pipeline. "
                    "Pipeline will run only 1 iteration.",
        ))

    if has_pm:
        # Check if ANY PMAgent step has on_next_iteration (not just the first)
        pm_has_routing = any(
            s.on_next_iteration
            for s in pipeline_def.steps
            if s.agent == "PMAgent"
        )
        if not pm_has_routing:
            pm_step = next(s for s in pipeline_def.steps if s.agent == "PMAgent")
            warnings.append(ValidationIssue(
                type="missing_iteration_routing",
                step=pm_step.step,
                agent="PMAgent",
                message="PMAgent has no on_next_iteration target. "
                        "Iteration loop will not function.",
            ))

    valid = len(errors) == 0
    return PipelineValidationResult(
        valid=valid,
        errors=errors,
        warnings=warnings,
        artifact_flow=artifact_flow,
    )
