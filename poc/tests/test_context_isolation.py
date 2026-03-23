"""
Context isolation verification tests.

Verify that ValidatorAgent receives ONLY the artifact YAML,
not other agents' system prompts or thinking process.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from registry.models import StepDefinition
from prompts.message_strategies import build_user_message
from registry.agent_registry import get_agent
from pipeline.state import PipelineState


def _make_state(**overrides) -> PipelineState:
    """Create a minimal PipelineState for testing."""
    base: PipelineState = {
        "user_story": "As a user, I want to log in.",
        "steps_completed": [],
        "latest_artifacts": {},
        "current_step_index": 0,
        "iteration_count": 1,
        "max_iterations": 3,
        "rework_count": 0,
        "max_reworks_per_gate": 3,
        "pipeline_status": "running",
    }
    base.update(overrides)
    return base


def test_validator_user_message_contains_only_artifact():
    """ValidatorAgent user message must contain only the artifact YAML."""
    from prompts.builder import build_system_prompt

    # Build ReqAgent system prompt to check it doesn't leak
    req_config = get_agent("ReqAgent")
    req_system_prompt = build_system_prompt(req_config)

    # State: ReqAgent has produced a UC artifact
    state = _make_state(
        steps_completed=[{
            "step_id": "step_1_ReqAgent",
            "agent_id": "ReqAgent",
            "artifact_yaml": "artifact_id: UC-01\nartifact_type: UseCaseModelArtifact\n",
            "artifact_type": "UseCaseModelArtifact",
            "model_used": "test-model",
            "validation_result": None,
        }],
        latest_artifacts={
            "UseCaseModelArtifact": "artifact_id: UC-01\nartifact_type: UseCaseModelArtifact\n",
        },
    )

    validator_config = get_agent("ValidatorAgent")
    validator_step = StepDefinition(step=2, agent="ValidatorAgent", on_fail="ReqAgent")

    user_msg = build_user_message(validator_config, validator_step, state)

    # ReqAgent system prompt content must NOT appear in user message
    assert "ReqAgent Role" not in user_msg, \
        "ReqAgent system prompt leaked into ValidatorAgent user message!"

    # The UC artifact MUST appear in the user message
    assert "UC-01" in user_msg, "UC artifact not present in ValidatorAgent user message"

    # System prompt keywords must not appear
    assert "AgentCommon" not in user_msg, "Common prompt leaked into user message"

    print("PASS: Context isolation verified — ValidatorAgent received only the artifact")


def test_req_agent_does_not_receive_validator_system_prompt():
    """ReqAgent rework message must not contain ValidatorAgent's system prompt."""
    state = _make_state(
        iteration_count=1,
        latest_artifacts={
            "UseCaseModelArtifact": "artifact_id: UC-01\n",
            "ValidationReportArtifact": "validation_result: fail\nblocking_reason: missing fields\n",
        },
    )

    req_config = get_agent("ReqAgent")
    req_step = StepDefinition(step=1, agent="ReqAgent")

    user_msg = build_user_message(req_config, req_step, state)

    # Must contain the validation report and previous artifact
    assert "fail" in user_msg
    assert "UC-01" in user_msg

    # Must NOT contain ValidatorAgent's system prompt content
    assert "ADVERSARIAL" not in user_msg
    assert "ValidatorAgent Role" not in user_msg

    print("PASS: ReqAgent rework message contains only artifacts")


if __name__ == "__main__":
    test_validator_user_message_contains_only_artifact()
    test_req_agent_does_not_receive_validator_system_prompt()
    print("\nAll context isolation tests passed.")
