"""Provider-agnostic LLM client for OpenSDLC.

Supports Anthropic (Claude), Google (Gemini), OpenAI (GPT), and Ollama.
Provider is selected via OPENSDLC_LLM_PROVIDER env var or config defaults.
Includes automatic retry with backoff for rate-limit (429) errors.
Detects daily quota exhaustion and provides clear error messages.
"""

import hashlib
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import httpx

from app.core.config import (
    get_anthropic_api_key,
    get_google_api_key,
    get_llm_provider,
    get_model,
    get_ollama_base_url,
    get_openai_api_key,
)

logger = logging.getLogger(__name__)

Provider = Literal["anthropic", "google", "openai", "ollama"]


@dataclass(frozen=True)
class LLMResponse:
    """Unified response from any LLM provider."""

    text: str
    model: str
    provider: Provider
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None


def _call_anthropic(system: str, user_message: str, model: str, max_tokens: int) -> LLMResponse:
    import anthropic

    client = anthropic.Anthropic(api_key=get_anthropic_api_key())
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_message}],
    )
    usage = response.usage
    content_block = response.content[0]
    text = getattr(content_block, "text", None)
    if text is None:
        logger.warning(
            "[LLM] Anthropic API returned non-text content block (model=%s, type=%s)",
            model,
            getattr(content_block, "type", "unknown"),
        )
        text = ""

    return LLMResponse(
        text=text,
        model=model,
        provider="anthropic",
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", None),
        cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", None),
    )


_google_cache_store: dict[str, str] = {}


def _extract_google_text(response, model: str) -> str:
    """Google API 응답에서 텍스트를 안전하게 추출한다."""
    text = response.text
    if text is None:
        # 진단 정보 수집
        finish_reason = "unknown"
        if response.candidates:
            finish_reason = getattr(response.candidates[0], "finish_reason", "unknown")
        logger.warning(
            "[LLM] Google API returned None text (model=%s, finish_reason=%s). "
            "Possible causes: safety filter, empty response, non-text content.",
            model,
            finish_reason,
        )
        text = ""
    return text


def _call_google(system: str, user_message: str, model: str, max_tokens: int) -> LLMResponse:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=get_google_api_key())

    cache_key = hashlib.sha256(f"{model}:{system}".encode()).hexdigest()[:16]
    cached_content_name = _google_cache_store.get(cache_key)

    if cached_content_name:
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    cached_content=cached_content_name,
                    max_output_tokens=max_tokens,
                ),
            )
            usage = response.usage_metadata
            cache_read = getattr(usage, "cached_content_token_count", 0) or 0
            return LLMResponse(
                text=_extract_google_text(response, model),
                model=model,
                provider="google",
                input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
                output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
                cache_read_tokens=cache_read or None,
            )
        except Exception:
            logger.debug("Google cached content expired or invalid, recreating")
            _google_cache_store.pop(cache_key, None)

    try:
        cache = client.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                system_instruction=system,
            ),
        )
        _google_cache_store[cache_key] = cache.name
        logger.debug("Google cache created: %s", cache.name)

        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                cached_content=cache.name,
                max_output_tokens=max_tokens,
            ),
        )
        usage = response.usage_metadata
        cache_creation = getattr(usage, "cached_content_token_count", 0) or 0
        return LLMResponse(
            text=_extract_google_text(response, model),
            model=model,
            provider="google",
            input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
            cache_creation_tokens=cache_creation or None,
        )
    except Exception as cache_exc:
        logger.debug("Google caching unavailable (%s), falling back to direct call", cache_exc)

    response = client.models.generate_content(
        model=model,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        ),
    )
    usage = response.usage_metadata
    return LLMResponse(
        text=_extract_google_text(response, model),
        model=model,
        provider="google",
        input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
        output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
    )


def _call_openai(system: str, user_message: str, model: str, max_tokens: int) -> LLMResponse:
    from openai import OpenAI

    client = OpenAI(api_key=get_openai_api_key())
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    )
    usage = response.usage
    text = response.choices[0].message.content
    if text is None:
        logger.warning(
            "[LLM] OpenAI API returned None content (model=%s, finish_reason=%s)",
            model,
            response.choices[0].finish_reason,
        )
        text = ""

    return LLMResponse(
        text=text,
        model=model,
        provider="openai",
        input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
        output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
    )


def _call_ollama(system: str, user_message: str, model: str, max_tokens: int) -> LLMResponse:
    response = httpx.post(
        f"{get_ollama_base_url()}/api/chat",
        json={
            "model": model,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
        },
        timeout=300.0,
    )
    response.raise_for_status()
    data = response.json()
    message = data.get("message") or {}
    text = message.get("content")
    if text is None:
        logger.warning("[LLM] Ollama API returned None content (model=%s)", model)
        text = ""

    return LLMResponse(
        text=text,
        model=data.get("model", model),
        provider="ollama",
        input_tokens=data.get("prompt_eval_count"),
        output_tokens=data.get("eval_count"),
    )


_PROVIDERS: dict[Provider, callable] = {
    "anthropic": _call_anthropic,
    "google": _call_google,
    "openai": _call_openai,
    "ollama": _call_ollama,
}


def _default_quality_check(response: LLMResponse, min_chars: int) -> str | None:
    if not response.text or not response.text.strip():
        return "empty response"
    if len(response.text.strip()) < min_chars:
        return f"response too short ({len(response.text.strip())} chars < {min_chars} min)"
    return None


class QuotaExhaustedError(Exception):
    """Raised when the daily API quota is exhausted."""

    def __init__(self, provider: str, model: str, message: str, retry_after: float | None = None):
        self.provider = provider
        self.model = model
        self.retry_after = retry_after
        super().__init__(message)


def _extract_retry_delay(exc: Exception, default: float = 60.0) -> float:
    msg = str(exc)
    m = re.search(r"retry\s*(?:in|Delay[\"']?:\s*[\"']?)\s*([\d.]+)\s*s", msg, re.IGNORECASE)
    if m:
        return float(m.group(1)) + 2.0
    return default


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "resource_exhausted" in msg or "rate" in msg


def _is_daily_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "quota" in msg and ("per day" in msg or "free_tier" in msg or "freetier" in msg)


def call_llm(
    system: str,
    user_message: str,
    *,
    model: str | None = None,
    provider: Provider | None = None,
    max_tokens: int = 4096,
    max_retries: int = 2,
    min_response_chars: int = 500,
    rate_limit_retries: int = 3,
    quality_check: Callable[[LLMResponse], str | None] | None = None,
) -> LLMResponse:
    """Call LLM with provider-agnostic interface and automatic retry."""
    resolved_provider = provider or get_llm_provider()
    resolved_model = model or get_model()

    call_fn = _PROVIDERS.get(resolved_provider)
    if call_fn is None:
        raise ValueError(
            f"Unknown LLM provider: {resolved_provider!r}. "
            f"Supported: {', '.join(_PROVIDERS)}"
        )

    last_response: LLMResponse | None = None

    for attempt in range(1, max_retries + 2):
        logger.info(
            "[LLM] %s/%s — system=%d chars, user=%d chars (attempt %d/%d)",
            resolved_provider,
            resolved_model,
            len(system),
            len(user_message),
            attempt,
            max_retries + 1,
        )

        response: LLMResponse | None = None
        for rl_attempt in range(1, rate_limit_retries + 1):
            try:
                response = call_fn(system, user_message, resolved_model, max_tokens)
                break
            except Exception as exc:
                if not _is_rate_limit_error(exc):
                    raise

                if _is_daily_quota_error(exc):
                    delay = _extract_retry_delay(exc)
                    raise QuotaExhaustedError(
                        provider=resolved_provider,
                        model=resolved_model,
                        message=(
                            f"Daily API quota exhausted for {resolved_provider}/{resolved_model}. "
                            f"The free tier limit has been reached. Options:\n"
                            f"  1. Wait ~{delay:.0f}s and retry\n"
                            f"  2. Switch to a different provider: "
                            f"OPENSDLC_LLM_PROVIDER=anthropic|openai|ollama\n"
                            f"  3. Upgrade to a paid API plan\n"
                            f"Partial pipeline output has been saved."
                        ),
                        retry_after=delay,
                    ) from exc

                if rl_attempt < rate_limit_retries:
                    delay = _extract_retry_delay(exc)
                    logger.warning(
                        "[LLM] Rate limit hit (attempt %d/%d) — waiting %.0fs before retry...",
                        rl_attempt,
                        rate_limit_retries,
                        delay,
                    )
                    print(
                        f"\n[Rate Limit] API 요청 한도 초과 — {delay:.0f}초 후 재시도 "
                        f"({rl_attempt}/{rate_limit_retries})..."
                    )
                    time.sleep(delay)
                else:
                    raise

        assert response is not None
        last_response = response

        cache_info = ""
        if response.cache_read_tokens:
            cache_info = f", cache_read={response.cache_read_tokens}"
        elif response.cache_creation_tokens:
            cache_info = f", cache_created={response.cache_creation_tokens}"
        
        response_text = response.text or ""
        logger.info(
            "[LLM] response — %d chars (in=%s, out=%s tokens%s)",
            len(response_text),
            response.input_tokens,
            response.output_tokens,
            cache_info,
        )

        if quality_check is not None:
            issue = quality_check(response)
        else:
            issue = _default_quality_check(response, min_response_chars)

        if issue is None:
            return response

        if attempt <= max_retries:
            logger.warning(
                "[LLM] quality check failed: %s — retrying (%d/%d)",
                issue,
                attempt,
                max_retries,
            )
            time.sleep(1)
        else:
            logger.warning(
                "[LLM] quality check failed after %d attempts: %s — returning best effort",
                max_retries + 1,
                issue,
            )

    return last_response  # type: ignore[return-value]
