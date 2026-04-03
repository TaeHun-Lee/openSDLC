"""Tests for pipeline dry-run / validation endpoint."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from app.core.registry.models import PipelineDefinition, StepDefinition
from app.models.responses import PipelineValidationResult
from app.services.pipeline_compiler import validate_pipeline_runtime


class TestValidateEndpoint:
    """Integration tests for POST /api/pipelines/{name}/validate."""

    def test_validate_existing_pipeline(self, test_client: TestClient):
        resp = test_client.post("/api/pipelines/full_spiral/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert "valid" in data
        assert "errors" in data
        assert "warnings" in data
        assert "artifact_flow" in data
        assert isinstance(data["artifact_flow"], list)
        assert len(data["artifact_flow"]) > 0

    def test_validate_nonexistent_pipeline(self, test_client: TestClient):
        resp = test_client.post("/api/pipelines/nonexistent_xyz/validate")
        assert resp.status_code == 404

    def test_validate_returns_artifact_flow(self, test_client: TestClient):
        resp = test_client.post("/api/pipelines/full_spiral/validate")
        data = resp.json()
        flow = data["artifact_flow"]
        # First step is PMAgent
        assert flow[0]["agent"] == "PMAgent"
        assert flow[0]["step"] == 1
        # Each entry has produces and consumes
        for entry in flow:
            assert "produces" in entry
            assert "consumes" in entry


class TestValidatePipelineRuntime:
    """Unit tests for validate_pipeline_runtime()."""

    def _make_pipeline(self, steps: list[StepDefinition], **kwargs) -> PipelineDefinition:
        defaults = {"name": "test", "max_iterations": 3, "max_reworks_per_gate": 3}
        defaults.update(kwargs)
        return PipelineDefinition(steps=steps, **defaults)

    def test_valid_simple_pipeline(self):
        """A basic ReqAgent -> ValidatorAgent pipeline should pass."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent"),
            StepDefinition(step=2, agent="ValidatorAgent", on_fail="ReqAgent"),
        ], max_iterations=1)
        result = validate_pipeline_runtime(pipeline)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_unknown_agent_is_error(self):
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="FakeAgent"),
        ], max_iterations=1)
        result = validate_pipeline_runtime(pipeline)
        assert result.valid is False
        assert any(e.type == "unknown_agent" for e in result.errors)
        assert result.errors[0].agent == "FakeAgent"

    def test_missing_api_key_is_warning(self):
        """When provider's API key is empty, a warning should be raised."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent", provider="anthropic"),
        ], max_iterations=1)
        with patch("app.services.pipeline_compiler.get_anthropic_api_key", return_value=""):
            result = validate_pipeline_runtime(pipeline)
        warnings_types = [w.type for w in result.warnings]
        assert "api_key_missing" in warnings_types
        assert result.valid is True  # warnings don't make it invalid

    def test_api_key_present_no_warning(self):
        """When API key is set, no warning should be raised."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent", provider="anthropic"),
        ], max_iterations=1)
        with patch("app.services.pipeline_compiler.get_anthropic_api_key", return_value="sk-test"):
            result = validate_pipeline_runtime(pipeline)
        api_warnings = [w for w in result.warnings if w.type == "api_key_missing"]
        assert len(api_warnings) == 0

    def test_ollama_provider_no_api_key_warning(self):
        """Ollama is a local provider and should not require an API key."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent", provider="ollama"),
        ], max_iterations=1)
        result = validate_pipeline_runtime(pipeline)
        api_warnings = [w for w in result.warnings if w.type == "api_key_missing"]
        assert len(api_warnings) == 0

    def test_unreachable_rework_target_is_error(self):
        """on_fail pointing to an agent not in preceding steps should be an error."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent"),
            StepDefinition(step=2, agent="ValidatorAgent", on_fail="CodeAgent"),
        ], max_iterations=1)
        result = validate_pipeline_runtime(pipeline)
        assert result.valid is False
        assert any(e.type == "unreachable_rework_target" for e in result.errors)

    def test_valid_rework_target(self):
        """on_fail pointing to a preceding agent should not produce an error."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent"),
            StepDefinition(step=2, agent="ValidatorAgent", on_fail="ReqAgent"),
        ], max_iterations=1)
        result = validate_pipeline_runtime(pipeline)
        rework_errors = [e for e in result.errors if e.type == "unreachable_rework_target"]
        assert len(rework_errors) == 0

    def test_no_pm_agent_with_multi_iteration_warning(self):
        """max_iterations > 1 without PMAgent should produce a warning."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent"),
            StepDefinition(step=2, agent="CodeAgent"),
        ], max_iterations=3)
        result = validate_pipeline_runtime(pipeline)
        assert any(w.type == "no_pm_agent" for w in result.warnings)

    def test_pm_agent_without_on_next_iteration_warning(self):
        """PMAgent without on_next_iteration should produce a warning."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent"),
            StepDefinition(step=2, agent="PMAgent"),  # no on_next_iteration
        ], max_iterations=3)
        result = validate_pipeline_runtime(pipeline)
        assert any(w.type == "missing_iteration_routing" for w in result.warnings)

    def test_pm_agent_with_on_next_iteration_no_warning(self):
        """PMAgent with on_next_iteration should not produce that warning."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent"),
            StepDefinition(step=2, agent="PMAgent", on_next_iteration="ReqAgent"),
        ], max_iterations=3)
        result = validate_pipeline_runtime(pipeline)
        iter_warnings = [w for w in result.warnings if w.type == "missing_iteration_routing"]
        assert len(iter_warnings) == 0

    def test_artifact_flow_tracks_outputs(self):
        """artifact_flow should show what each step produces and consumes."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent"),
            StepDefinition(step=2, agent="ValidatorAgent", on_fail="ReqAgent"),
        ], max_iterations=1)
        result = validate_pipeline_runtime(pipeline)
        assert len(result.artifact_flow) == 2
        # ReqAgent produces something
        assert result.artifact_flow[0].agent == "ReqAgent"
        assert len(result.artifact_flow[0].produces) > 0

    def test_single_iteration_no_pm_no_warning(self):
        """max_iterations=1 without PMAgent should NOT produce a warning."""
        pipeline = self._make_pipeline([
            StepDefinition(step=1, agent="ReqAgent"),
            StepDefinition(step=2, agent="CodeAgent"),
        ], max_iterations=1)
        result = validate_pipeline_runtime(pipeline)
        pm_warnings = [w for w in result.warnings if w.type == "no_pm_agent"]
        assert len(pm_warnings) == 0
