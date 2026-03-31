"""Test suite for run creation including workspace_path."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_start_run_with_workspace_path(test_client: TestClient):
    """Verify that POST /api/runs handles workspace_path correctly."""
    resp = test_client.post("/api/runs", json={
        "pipeline": "full_spiral",
        "user_story": "Test user story for workspace path verification. It must be at least ten characters long.",
        "workspace_path": "/tmp/test-workspace"
    })
    
    # 201 Created is expected
    assert resp.status_code == 201
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "pending"
    assert data["pipeline"] == "full_spiral"

def test_start_run_minimal(test_client: TestClient):
    """Verify that POST /api/runs works with minimal payload."""
    resp = test_client.post("/api/runs", json={
        "pipeline": "full_spiral",
        "user_story": "Minimal test story for verification."
    })
    
    assert resp.status_code == 201
    assert "run_id" in resp.json()
