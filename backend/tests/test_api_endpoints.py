"""Integration tests for API endpoints."""

from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.db import repository as repo
from app.db.session import init_db
from app.routers.runs import get_artifacts
from app.services.run_manager import RunManager


class TestHealthEndpoint:
    def test_health_returns_ok(self, test_client: TestClient):
        resp = test_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "llm_provider" in data
        assert "model" in data


class TestProjectsCRUD:
    def test_create_and_list_project(self, test_client: TestClient):
        # Create
        resp = test_client.post("/api/projects", json={
            "name": "Test Project",
            "description": "A test project",
        })
        assert resp.status_code == 201
        project = resp.json()
        assert project["name"] == "Test Project"
        project_id = project["project_id"]

        # List
        resp = test_client.get("/api/projects")
        assert resp.status_code == 200
        projects = resp.json()
        assert any(p["project_id"] == project_id for p in projects)

    def test_get_project_detail(self, test_client: TestClient):
        resp = test_client.post("/api/projects", json={"name": "Detail Test"})
        project_id = resp.json()["project_id"]

        resp = test_client.get(f"/api/projects/{project_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail Test"

    def test_update_project(self, test_client: TestClient):
        resp = test_client.post("/api/projects", json={"name": "Original"})
        project_id = resp.json()["project_id"]

        resp = test_client.put(f"/api/projects/{project_id}", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_delete_project(self, test_client: TestClient):
        resp = test_client.post("/api/projects", json={"name": "ToDelete"})
        project_id = resp.json()["project_id"]

        resp = test_client.delete(f"/api/projects/{project_id}")
        assert resp.status_code == 204

        resp = test_client.get(f"/api/projects/{project_id}")
        assert resp.status_code == 404

    def test_get_nonexistent_project(self, test_client: TestClient):
        resp = test_client.get("/api/projects/nonexistent")
        assert resp.status_code == 404


class TestPipelinesEndpoint:
    def test_list_pipelines(self, test_client: TestClient):
        resp = test_client.get("/api/pipelines")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_nonexistent_pipeline(self, test_client: TestClient):
        resp = test_client.get("/api/pipelines/nonexistent_pipeline_xyz")
        assert resp.status_code == 404


class TestAgentsEndpoint:
    def test_list_agents(self, test_client: TestClient):
        resp = test_client.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        assert isinstance(agents, list)
        if agents:
            assert "agent_id" in agents[0]

    def test_get_nonexistent_agent(self, test_client: TestClient):
        resp = test_client.get("/api/agents/NonExistentAgent")
        assert resp.status_code == 404


class TestRunsEndpoint:
    def test_list_runs_empty(self, test_client: TestClient):
        resp = test_client.get("/api/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_nonexistent_run(self, test_client: TestClient):
        resp = test_client.get("/api/runs/nonexistent-run-id")
        assert resp.status_code == 404

    def test_get_progress_nonexistent(self, test_client: TestClient):
        resp = test_client.get("/api/runs/nonexistent/progress")
        assert resp.status_code == 404

    def test_cancel_nonexistent(self, test_client: TestClient):
        resp = test_client.post("/api/runs/nonexistent/cancel")
        assert resp.status_code == 404


class TestIterationEndpoints:
    """Tests for GET /api/runs/{id}/iterations/{num} and sub-routes."""

    def _seed_run_with_iteration(self, test_client: TestClient):
        """Seed a run with one iteration and two steps directly via DB."""
        sf = test_client.app.state.session_factory
        run_id = "test-iter-run"
        now = time.time()
        with sf() as session:
            repo.create_run(session, run_id, "test-pipe", "test story")
            repo.update_run_status(session, run_id, "completed", finished_at=now)
            repo.create_iteration(session, run_id, 1, started_at=now)
            repo.update_iteration(session, run_id, 1, status="completed", finished_at=now)
            repo.create_step(
                session, run_id, 1, 1, "ReqAgent", started_at=now,
            )
            repo.update_step(
                session, run_id, 1, 1,
                verdict="pass", model_used="test-model", provider="google",
                input_tokens=100, output_tokens=200, finished_at=now,
            )
            repo.create_step(
                session, run_id, 1, 2, "ValidatorAgent", started_at=now,
            )
            repo.update_step(
                session, run_id, 1, 2,
                verdict="pass", model_used="test-model", provider="google",
                input_tokens=150, output_tokens=250, finished_at=now,
            )
        return run_id

    def test_get_iteration(self, test_client: TestClient):
        run_id = self._seed_run_with_iteration(test_client)
        resp = test_client.get(f"/api/runs/{run_id}/iterations/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["iteration_num"] == 1
        assert data["status"] == "completed"
        assert len(data["steps"]) == 2
        assert data["steps"][0]["agent_name"] == "ReqAgent"
        assert data["steps"][1]["agent_name"] == "ValidatorAgent"

    def test_get_iteration_not_found(self, test_client: TestClient):
        run_id = self._seed_run_with_iteration(test_client)
        resp = test_client.get(f"/api/runs/{run_id}/iterations/99")
        assert resp.status_code == 404

    def test_get_iteration_run_not_found(self, test_client: TestClient):
        resp = test_client.get("/api/runs/nonexistent/iterations/1")
        assert resp.status_code == 404

    def test_get_iteration_steps(self, test_client: TestClient):
        run_id = self._seed_run_with_iteration(test_client)
        resp = test_client.get(f"/api/runs/{run_id}/iterations/1/steps")
        assert resp.status_code == 200
        steps = resp.json()
        assert len(steps) == 2
        assert steps[0]["step_num"] == 1
        assert steps[0]["verdict"] == "pass"
        assert steps[0]["input_tokens"] == 100

    def test_get_iteration_artifacts_empty(self, test_client: TestClient):
        run_id = self._seed_run_with_iteration(test_client)
        resp = test_client.get(f"/api/runs/{run_id}/iterations/1/artifacts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_id
        assert data["artifacts"] == []
        assert data["code_files"] == []


class TestArtifactsEndpoint:
    def test_get_artifacts_skips_missing_artifact_files(self, tmp_path: Path):
        sf = init_db(tmp_path / "test.db", run_migrations=False)
        run_id = "test-missing-artifact-run"
        now = time.time()
        missing_artifact_path = tmp_path / "missing-artifact.yaml"

        with sf() as session:
            repo.create_run(session, run_id, "test-pipe", "test story")
            repo.update_run_status(session, run_id, "completed", finished_at=now)
            repo.create_iteration(session, run_id, 1, started_at=now)
            repo.update_iteration(session, run_id, 1, status="completed", finished_at=now)
            repo.create_step(session, run_id, 1, 1, "ReqAgent", started_at=now)
            repo.update_step(
                session, run_id, 1, 1,
                verdict="pass", model_used="test-model", provider="google",
                input_tokens=100, output_tokens=200, finished_at=now,
            )
            repo.insert_artifact(
                session, run_id, 1, 1,
                agent_name="ReqAgent",
                artifact_type="UseCaseModelArtifact",
                artifact_id="REQ-404",
                file_path=str(missing_artifact_path),
            )

        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    session_factory=sf,
                    run_manager=RunManager(sf),
                ),
            ),
        )

        result = get_artifacts(run_id, request)

        assert result.run_id == run_id
        assert result.artifacts == []
        assert result.code_files == []
