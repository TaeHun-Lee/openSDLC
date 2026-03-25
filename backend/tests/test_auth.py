"""Tests for API Key authentication."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestAuthDisabled:
    """When OPENSDLC_API_KEY is empty, all endpoints should be accessible."""

    def test_health_accessible(self, test_client: TestClient):
        resp = test_client.get("/api/health")
        assert resp.status_code == 200

    def test_agents_accessible_without_key(self, test_client: TestClient):
        resp = test_client.get("/api/agents")
        assert resp.status_code == 200

    def test_projects_accessible_without_key(self, test_client: TestClient):
        resp = test_client.get("/api/projects")
        assert resp.status_code == 200


class TestAuthEnabled:
    """When OPENSDLC_API_KEY is set, protected endpoints require X-API-Key header."""

    def test_health_still_public(self, authed_client: TestClient):
        resp = authed_client.get("/api/health")
        assert resp.status_code == 200

    def test_agents_rejected_without_key(self, authed_client: TestClient):
        resp = authed_client.get("/api/agents")
        assert resp.status_code == 401

    def test_agents_rejected_with_wrong_key(self, authed_client: TestClient):
        resp = authed_client.get("/api/agents", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 403

    def test_agents_accessible_with_correct_key(self, authed_client: TestClient):
        resp = authed_client.get(
            "/api/agents",
            headers={"X-API-Key": "test-secret-key"},
        )
        assert resp.status_code == 200

    def test_projects_require_key(self, authed_client: TestClient):
        resp = authed_client.get("/api/projects")
        assert resp.status_code == 401
        resp = authed_client.get(
            "/api/projects",
            headers={"X-API-Key": "test-secret-key"},
        )
        assert resp.status_code == 200
