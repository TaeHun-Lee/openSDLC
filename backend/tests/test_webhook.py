"""Tests for webhook notification logic."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.services.event_bus import EventBus
from app.services.run_manager import RunManager, RunRecord, RunStatus


def _make_record(
    *,
    status: RunStatus = RunStatus.COMPLETED,
    webhook_url: str | None = "https://example.com/hook",
    webhook_events: list[str] | None = None,
) -> RunRecord:
    return RunRecord(
        run_id="test-run-1",
        pipeline_name="test-pipe",
        user_story="test story",
        max_iterations=3,
        status=status,
        event_bus=EventBus(),
        created_at=time.time() - 10,
        finished_at=time.time(),
        final_state={
            "steps_completed": [
                {"input_tokens": 100, "output_tokens": 200},
                {"input_tokens": 150, "output_tokens": 250},
            ],
            "iteration_count": 2,
        },
        webhook_url=webhook_url,
        webhook_events=webhook_events,
    )


class TestSendWebhook:
    @pytest.mark.asyncio
    async def test_sends_webhook_on_completed(self, tmp_db):
        manager = RunManager(session_factory=tmp_db)
        record = _make_record(status=RunStatus.COMPLETED)

        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await manager._send_webhook(record)

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://example.com/hook"
            payload = call_args[1]["json"]
            assert payload["run_id"] == "test-run-1"
            assert payload["status"] == "completed"
            assert payload["total_tokens"] == 700  # 100+200+150+250
            assert payload["iterations_completed"] == 2

    @pytest.mark.asyncio
    async def test_skips_webhook_when_no_url(self, tmp_db):
        manager = RunManager(session_factory=tmp_db)
        record = _make_record(webhook_url=None)

        with patch("httpx.AsyncClient") as mock_client_cls:
            await manager._send_webhook(record)
            mock_client_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_webhook_when_status_not_in_events(self, tmp_db):
        manager = RunManager(session_factory=tmp_db)
        record = _make_record(
            status=RunStatus.COMPLETED,
            webhook_events=["failed"],  # only interested in failures
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            await manager._send_webhook(record)
            mock_client_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_webhook_when_status_in_events(self, tmp_db):
        manager = RunManager(session_factory=tmp_db)
        record = _make_record(
            status=RunStatus.FAILED,
            webhook_events=["failed", "cancelled"],
        )
        record.error = "LLM quota exhausted"

        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await manager._send_webhook(record)

            payload = mock_client.post.call_args[1]["json"]
            assert payload["status"] == "failed"
            assert payload["error"] == "LLM quota exhausted"

    @pytest.mark.asyncio
    async def test_retries_on_failure(self, tmp_db):
        manager = RunManager(session_factory=tmp_db)
        record = _make_record()

        mock_response_fail = AsyncMock()
        mock_response_fail.status_code = 500
        mock_response_ok = AsyncMock()
        mock_response_ok.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = [mock_response_fail, mock_response_ok]
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await manager._send_webhook(record, max_retries=2)

            assert mock_client.post.call_count == 2


class TestWebhookDbPersistence:
    def test_webhook_url_persisted_in_db(self, tmp_db):
        from app.db import repository as repo

        with tmp_db() as session:
            run = repo.create_run(
                session, "wh-run", "pipe", "story",
                webhook_url="https://example.com/hook",
                webhook_events='["completed"]',
            )
        with tmp_db() as session:
            db_run = repo.get_run(session, "wh-run")
            assert db_run.webhook_url == "https://example.com/hook"
            assert db_run.webhook_events == '["completed"]'

    def test_webhook_url_defaults_to_none(self, tmp_db):
        from app.db import repository as repo

        with tmp_db() as session:
            repo.create_run(session, "no-wh-run", "pipe", "story")
        with tmp_db() as session:
            db_run = repo.get_run(session, "no-wh-run")
            assert db_run.webhook_url is None
            assert db_run.webhook_events is None
