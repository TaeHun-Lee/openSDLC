from __future__ import annotations

from unittest.mock import Mock

import httpx

from app.core.llm_client import call_llm


def test_call_llm_with_ollama_provider(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "model": "gemma3",
        "message": {"content": "local response"},
        "prompt_eval_count": 123,
        "eval_count": 45,
    }
    response.raise_for_status.return_value = None

    captured: dict[str, object] = {}

    def fake_post(url: str, *, json: dict, timeout: float):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return response

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")

    result = call_llm(
        "system prompt",
        "user prompt",
        provider="ollama",
        model="gemma3",
        max_retries=0,
        rate_limit_retries=1,
        min_response_chars=1,
    )

    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["timeout"] == 300.0
    assert captured["json"] == {
        "model": "gemma3",
        "stream": False,
        "options": {"num_predict": 4096},
        "messages": [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"},
        ],
    }
    assert result.provider == "ollama"
    assert result.model == "gemma3"
    assert result.text == "local response"
    assert result.input_tokens == 123
    assert result.output_tokens == 45
