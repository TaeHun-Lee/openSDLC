"""Provider-agnostic LLM client for OpenSDLC PoC.

Supports Anthropic (Claude), Google (Gemini), and OpenAI (GPT).
Provider is selected via OPENSDLC_LLM_PROVIDER env var or config.py defaults.
Includes automatic retry with backoff for rate-limit (429) errors.
"""

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from config import (
    ANTHROPIC_API_KEY,
    GOOGLE_API_KEY,
    LLM_PROVIDER,
    MODEL,
    OPENAI_API_KEY,
)

logger = logging.getLogger(__name__)

Provider = Literal["anthropic", "google", "openai"]


@dataclass(frozen=True)
class LLMResponse:
    """Unified response from any LLM provider."""
    text: str
    model: str
    provider: Provider
    input_tokens: int | None = None
    output_tokens: int | None = None


def _call_anthropic(system: str, user_message: str, model: str, max_tokens: int) -> LLMResponse:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return LLMResponse(
        text=response.content[0].text,
        model=model,
        provider="anthropic",
        input_tokens=getattr(response.usage, "input_tokens", None),
        output_tokens=getattr(response.usage, "output_tokens", None),
    )


def _call_google(system: str, user_message: str, model: str, max_tokens: int) -> LLMResponse:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GOOGLE_API_KEY)
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
        text=response.text,
        model=model,
        provider="google",
        input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
        output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
    )


def _call_openai(system: str, user_message: str, model: str, max_tokens: int) -> LLMResponse:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    )
    usage = response.usage
    return LLMResponse(
        text=response.choices[0].message.content,
        model=model,
        provider="openai",
        input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
        output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
    )


_PROVIDERS: dict[Provider, callable] = {
    "anthropic": _call_anthropic,
    "google": _call_google,
    "openai": _call_openai,
}


def _default_quality_check(response: LLMResponse, min_chars: int) -> str | None:
    """Default response quality check.

    Returns None if quality is acceptable, or an error description string.
    """
    if not response.text or not response.text.strip():
        return "empty response"
    if len(response.text.strip()) < min_chars:
        return f"response too short ({len(response.text.strip())} chars < {min_chars} min)"
    return None


def _extract_retry_delay(exc: Exception, default: float = 60.0) -> float:
    """Extract retry delay from a rate-limit error message.

    Looks for patterns like 'retry in 39s', 'retry in 39.25s', 'retryDelay: 39s'.
    Returns the parsed delay in seconds, or `default` if not found.
    """
    msg = str(exc)
    m = re.search(r"retry\s*(?:in|Delay[\"']?:\s*[\"']?)\s*([\d.]+)\s*s", msg, re.IGNORECASE)
    if m:
        return float(m.group(1)) + 2.0  # add small buffer
    return default


def _is_rate_limit_error(exc: Exception) -> bool:
    """Check if an exception is a rate-limit (429 / RESOURCE_EXHAUSTED) error."""
    msg = str(exc).lower()
    return "429" in msg or "resource_exhausted" in msg or "rate" in msg


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
    """Call LLM with provider-agnostic interface and automatic retry.

    Args:
        system: System prompt.
        user_message: User message.
        model: Model name override (defaults to config.MODEL).
        provider: Provider override (defaults to config.LLM_PROVIDER).
        max_tokens: Max output tokens.
        max_retries: Number of retry attempts on quality failure (default 2).
        min_response_chars: Minimum acceptable response length in chars.
        rate_limit_retries: Number of retry attempts on 429 rate-limit errors (default 3).
        quality_check: Optional custom validator — receives LLMResponse,
            returns None if OK or an error description string.

    Returns:
        LLMResponse with text and metadata.
    """
    resolved_provider = provider or LLM_PROVIDER
    resolved_model = model or MODEL

    call_fn = _PROVIDERS.get(resolved_provider)
    if call_fn is None:
        raise ValueError(
            f"Unknown LLM provider: {resolved_provider!r}. "
            f"Supported: {', '.join(_PROVIDERS)}"
        )

    last_response: LLMResponse | None = None

    for attempt in range(1, max_retries + 2):  # +2: 1 initial + max_retries
        logger.info(
            "[LLM] %s/%s — system=%d chars, user=%d chars (attempt %d/%d)",
            resolved_provider,
            resolved_model,
            len(system),
            len(user_message),
            attempt,
            max_retries + 1,
        )

        # LLM call with rate-limit retry
        response: LLMResponse | None = None
        for rl_attempt in range(1, rate_limit_retries + 1):
            try:
                response = call_fn(system, user_message, resolved_model, max_tokens)
                break  # success
            except Exception as exc:
                if _is_rate_limit_error(exc) and rl_attempt < rate_limit_retries:
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
                    raise  # non-rate-limit error or retries exhausted

        assert response is not None
        last_response = response

        logger.info(
            "[LLM] response — %d chars (in=%s, out=%s tokens)",
            len(response.text),
            response.input_tokens,
            response.output_tokens,
        )

        # Run quality checks
        if quality_check is not None:
            issue = quality_check(response)
        else:
            issue = _default_quality_check(response, min_response_chars)

        if issue is None:
            return response

        # Quality check failed
        if attempt <= max_retries:
            logger.warning(
                "[LLM] quality check failed: %s — retrying (%d/%d)",
                issue,
                attempt,
                max_retries,
            )
            time.sleep(1)  # brief pause before retry
        else:
            logger.warning(
                "[LLM] quality check failed after %d attempts: %s — returning best effort",
                max_retries + 1,
                issue,
            )

    return last_response  # type: ignore[return-value]
