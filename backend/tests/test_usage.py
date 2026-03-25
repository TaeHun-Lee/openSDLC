"""Tests for token usage aggregation endpoints."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db import repository as repo


def _seed_run_with_steps(test_client: TestClient, run_id: str = "usage-run-1",
                         project_id: str | None = None) -> str:
    """Seed a run with iterations and steps that have token usage data."""
    sf = test_client.app.state.session_factory
    now = time.time()
    with sf() as session:
        repo.create_run(session, run_id, "test-pipe", "test story")
        if project_id:
            db_run = repo.get_run(session, run_id)
            db_run.project_id = project_id
            session.flush()

        # Iteration 1 with 2 steps
        repo.create_iteration(session, run_id, 1, started_at=now)
        repo.update_iteration(session, run_id, 1, status="completed", finished_at=now)
        repo.create_step(session, run_id, 1, 1, "ReqAgent", started_at=now)
        repo.update_step(
            session, run_id, 1, 1,
            verdict="pass", model_used="gemini-2.0-flash", provider="google",
            input_tokens=1000, output_tokens=2000,
            cache_read_tokens=500, cache_creation_tokens=100,
            finished_at=now,
        )
        repo.create_step(session, run_id, 1, 2, "ValidatorAgent", started_at=now)
        repo.update_step(
            session, run_id, 1, 2,
            verdict="pass", model_used="gemini-2.0-flash", provider="google",
            input_tokens=800, output_tokens=1500,
            cache_read_tokens=300, cache_creation_tokens=50,
            finished_at=now,
        )

        # Iteration 2 with 1 step using a different model
        repo.create_iteration(session, run_id, 2, started_at=now)
        repo.update_iteration(session, run_id, 2, status="completed", finished_at=now)
        repo.create_step(session, run_id, 2, 1, "CodeAgent", started_at=now)
        repo.update_step(
            session, run_id, 2, 1,
            verdict="pass", model_used="claude-sonnet-4-20250514", provider="anthropic",
            input_tokens=2000, output_tokens=5000,
            cache_read_tokens=1000, cache_creation_tokens=200,
            finished_at=now,
        )

        repo.update_run_status(session, run_id, "completed", finished_at=now)
    return run_id


class TestRunUsage:
    def test_get_run_usage(self, test_client: TestClient):
        run_id = _seed_run_with_steps(test_client)
        resp = test_client.get(f"/api/runs/{run_id}/usage")
        assert resp.status_code == 200
        data = resp.json()

        assert data["run_id"] == run_id
        assert data["total_input_tokens"] == 3800   # 1000+800+2000
        assert data["total_output_tokens"] == 8500   # 2000+1500+5000
        assert data["total_cache_read_tokens"] == 1800   # 500+300+1000
        assert data["total_cache_creation_tokens"] == 350  # 100+50+200

    def test_run_usage_by_model(self, test_client: TestClient):
        run_id = _seed_run_with_steps(test_client)
        resp = test_client.get(f"/api/runs/{run_id}/usage")
        data = resp.json()

        by_model = data["by_model"]
        assert "gemini-2.0-flash" in by_model
        assert by_model["gemini-2.0-flash"]["steps"] == 2
        assert by_model["gemini-2.0-flash"]["input_tokens"] == 1800
        assert by_model["gemini-2.0-flash"]["output_tokens"] == 3500
        assert by_model["gemini-2.0-flash"]["provider"] == "google"

        assert "claude-sonnet-4-20250514" in by_model
        assert by_model["claude-sonnet-4-20250514"]["steps"] == 1
        assert by_model["claude-sonnet-4-20250514"]["provider"] == "anthropic"

    def test_run_usage_by_agent(self, test_client: TestClient):
        run_id = _seed_run_with_steps(test_client)
        resp = test_client.get(f"/api/runs/{run_id}/usage")
        data = resp.json()

        by_agent = data["by_agent"]
        assert "ReqAgent" in by_agent
        assert by_agent["ReqAgent"]["steps"] == 1
        assert by_agent["ReqAgent"]["input_tokens"] == 1000
        assert "ValidatorAgent" in by_agent
        assert "CodeAgent" in by_agent

    def test_run_usage_by_iteration(self, test_client: TestClient):
        run_id = _seed_run_with_steps(test_client)
        resp = test_client.get(f"/api/runs/{run_id}/usage")
        data = resp.json()

        by_iter = data["by_iteration"]
        assert len(by_iter) == 2
        iter1 = by_iter[0]
        assert iter1["iteration_num"] == 1
        assert iter1["input_tokens"] == 1800   # 1000+800
        assert iter1["output_tokens"] == 3500   # 2000+1500
        assert iter1["step_count"] == 2
        iter2 = by_iter[1]
        assert iter2["iteration_num"] == 2
        assert iter2["step_count"] == 1

    def test_run_usage_not_found(self, test_client: TestClient):
        resp = test_client.get("/api/runs/nonexistent/usage")
        assert resp.status_code == 404

    def test_run_usage_empty(self, test_client: TestClient):
        """A run with no steps should return zero totals."""
        sf = test_client.app.state.session_factory
        with sf() as session:
            repo.create_run(session, "empty-run", "test-pipe", "story")
        resp = test_client.get("/api/runs/empty-run/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_input_tokens"] == 0
        assert data["total_output_tokens"] == 0
        assert data["by_model"] == {}
        assert data["by_agent"] == {}
        assert data["by_iteration"] == []


class TestProjectUsage:
    def test_get_project_usage(self, test_client: TestClient):
        # Create project
        resp = test_client.post("/api/projects", json={"name": "Usage Test"})
        project_id = resp.json()["project_id"]

        # Seed two runs under this project
        _seed_run_with_steps(test_client, "proj-run-1", project_id=project_id)
        _seed_run_with_steps(test_client, "proj-run-2", project_id=project_id)

        resp = test_client.get(f"/api/projects/{project_id}/usage")
        assert resp.status_code == 200
        data = resp.json()

        assert data["project_id"] == project_id
        assert data["total_runs"] == 2
        # Each run has 3800 input tokens
        assert data["total_input_tokens"] == 7600
        assert data["total_output_tokens"] == 17000

    def test_project_usage_by_model(self, test_client: TestClient):
        resp = test_client.post("/api/projects", json={"name": "Model Usage"})
        project_id = resp.json()["project_id"]
        _seed_run_with_steps(test_client, "model-run", project_id=project_id)

        resp = test_client.get(f"/api/projects/{project_id}/usage")
        data = resp.json()

        by_model = data["by_model"]
        assert "gemini-2.0-flash" in by_model
        assert "claude-sonnet-4-20250514" in by_model

    def test_project_usage_by_pipeline(self, test_client: TestClient):
        resp = test_client.post("/api/projects", json={"name": "Pipeline Usage"})
        project_id = resp.json()["project_id"]
        _seed_run_with_steps(test_client, "pipe-run", project_id=project_id)

        resp = test_client.get(f"/api/projects/{project_id}/usage")
        data = resp.json()

        by_pipeline = data["by_pipeline"]
        assert "test-pipe" in by_pipeline
        assert by_pipeline["test-pipe"]["runs"] == 1
        assert by_pipeline["test-pipe"]["input_tokens"] == 3800

    def test_project_usage_not_found(self, test_client: TestClient):
        resp = test_client.get("/api/projects/nonexistent/usage")
        assert resp.status_code == 404

    def test_project_usage_empty(self, test_client: TestClient):
        """A project with no runs should return zero totals."""
        resp = test_client.post("/api/projects", json={"name": "Empty"})
        project_id = resp.json()["project_id"]

        resp = test_client.get(f"/api/projects/{project_id}/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] == 0
        assert data["total_input_tokens"] == 0
        assert data["by_model"] == {}
        assert data["by_pipeline"] == {}
