"""Tests for pipeline resume functionality (improvement ③)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db import repository as repo
from app.db.session import init_db
from app.services.run_manager import RunManager, RunStatus


@pytest.fixture()
def db_with_failed_run(tmp_path: Path):
    """Create a DB with a failed run that has completed steps and artifacts."""
    sf = init_db(tmp_path / "test.db")
    run_id = "test-resume-run-001"
    pipeline_name = "poc_classic"

    with sf() as session:
        # Create run
        repo.create_run(
            session,
            run_id=run_id,
            pipeline_name=pipeline_name,
            user_story="할 일 관리 앱을 만들어줘",
            max_iterations=3,
        )
        repo.update_run_status(session, run_id, "failed", error="QuotaExhaustedError")

        # Create iteration 1
        repo.create_iteration(session, run_id, iteration_num=1, started_at=time.time())

        # Step 1: ReqAgent (completed)
        repo.create_step(
            session, run_id, iteration_num=1, step_num=1,
            agent_name="ReqAgent", started_at=time.time(),
        )
        repo.update_step(
            session, run_id, iteration_num=1, step_num=1,
            verdict=None, model_used="gemini-2.5-flash",
            provider="google", input_tokens=1000, output_tokens=2000,
            finished_at=time.time(),
        )

        # Save artifact for step 1
        artifact_dir = tmp_path / "runs" / run_id / "iteration-01" / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_yaml = (
            "artifact_id: REQ-001\n"
            "type: UseCaseModelArtifact\n"
            "use_cases:\n"
            "  - name: Add Todo\n"
            "    description: User adds a new todo item\n"
        )
        artifact_file = artifact_dir / "001_UseCaseModelArtifact.yaml"
        artifact_file.write_text(artifact_yaml)
        repo.insert_artifact(
            session, run_id, iteration_num=1, step_num=1,
            agent_name="ReqAgent",
            artifact_type="UseCaseModelArtifact",
            artifact_id="REQ-001",
            file_path=str(artifact_file),
        )

        # Step 2: ValidatorAgent (completed with pass)
        repo.create_step(
            session, run_id, iteration_num=1, step_num=2,
            agent_name="ValidatorAgent", started_at=time.time(),
        )
        repo.update_step(
            session, run_id, iteration_num=1, step_num=2,
            verdict="pass", model_used="gemini-2.5-flash",
            provider="google", input_tokens=1500, output_tokens=1000,
            finished_at=time.time(),
        )

        val_yaml = (
            "artifact_id: VAL-001\n"
            "type: ValidationReportArtifact\n"
            "validation_result: pass\n"
        )
        val_file = artifact_dir / "002_ValidationReportArtifact.yaml"
        val_file.write_text(val_yaml)
        repo.insert_artifact(
            session, run_id, iteration_num=1, step_num=2,
            agent_name="ValidatorAgent",
            artifact_type="ValidationReportArtifact",
            artifact_id="VAL-001",
            file_path=str(val_file),
        )

        # Step 3: CodeAgent (started but not finished — quota hit)
        repo.create_step(
            session, run_id, iteration_num=1, step_num=3,
            agent_name="CodeAgent", started_at=time.time(),
        )
        # No finished_at → incomplete step

    return sf, run_id, tmp_path


class TestRestorePipelineState:
    """Test that _restore_pipeline_state correctly rebuilds PipelineState from DB."""

    def test_restores_completed_steps_only(self, db_with_failed_run):
        sf, run_id, tmp_path = db_with_failed_run
        manager = RunManager(sf)

        state = manager._restore_pipeline_state(run_id)

        # Only 2 completed steps (ReqAgent + ValidatorAgent), not the incomplete CodeAgent
        assert len(state["steps_completed"]) == 2
        assert state["steps_completed"][0]["agent_id"] == "ReqAgent"
        assert state["steps_completed"][1]["agent_id"] == "ValidatorAgent"

    def test_restores_latest_artifacts(self, db_with_failed_run):
        sf, run_id, tmp_path = db_with_failed_run
        manager = RunManager(sf)

        state = manager._restore_pipeline_state(run_id)

        assert "UseCaseModelArtifact" in state["latest_artifacts"]
        assert "ValidationReportArtifact" in state["latest_artifacts"]
        assert "REQ-001" in state["latest_artifacts"]["UseCaseModelArtifact"]

    def test_restores_user_story(self, db_with_failed_run):
        sf, run_id, tmp_path = db_with_failed_run
        manager = RunManager(sf)

        state = manager._restore_pipeline_state(run_id)

        assert "할 일 관리 앱" in state["user_story"]

    def test_restores_iteration_count(self, db_with_failed_run):
        sf, run_id, tmp_path = db_with_failed_run
        manager = RunManager(sf)

        state = manager._restore_pipeline_state(run_id)

        assert state["iteration_count"] == 1
        assert state["pipeline_status"] == "running"

    def test_rework_count_reset_after_pass(self, db_with_failed_run):
        sf, run_id, tmp_path = db_with_failed_run
        manager = RunManager(sf)

        state = manager._restore_pipeline_state(run_id)

        # After a pass verdict, rework_count should be 0
        assert state["rework_count"] == 0

    def test_nonexistent_run_raises(self, db_with_failed_run):
        sf, _, _ = db_with_failed_run
        manager = RunManager(sf)

        with pytest.raises(ValueError, match="not found"):
            manager._restore_pipeline_state("nonexistent-id")


class TestResumeRunValidation:
    """Test resume_run input validation (without actually running the pipeline)."""

    @pytest.mark.asyncio
    async def test_resume_completed_run_raises(self, db_with_failed_run):
        sf, run_id, tmp_path = db_with_failed_run

        # Change status to completed
        with sf() as session:
            repo.update_run_status(session, run_id, "completed")

        manager = RunManager(sf)
        with pytest.raises(ValueError, match="cannot be resumed"):
            await manager.resume_run(run_id)

    @pytest.mark.asyncio
    async def test_resume_running_run_raises(self, db_with_failed_run):
        sf, run_id, tmp_path = db_with_failed_run

        with sf() as session:
            repo.update_run_status(session, run_id, "running")

        manager = RunManager(sf)
        with pytest.raises(ValueError, match="cannot be resumed"):
            await manager.resume_run(run_id)

    @pytest.mark.asyncio
    async def test_resume_nonexistent_run_raises(self, db_with_failed_run):
        sf, _, _ = db_with_failed_run
        manager = RunManager(sf)

        with pytest.raises(ValueError, match="not found"):
            await manager.resume_run("no-such-run")
