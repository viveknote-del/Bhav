"""
Single abstraction layer for all LLM calls.

HARD RULE: Never import anthropic/openai directly from routers, services, or workers.
All AI calls go through this module.

Provider order (automatic fallback):
  1. Anthropic Claude  — primary
  2. OpenAI           — fallback on rate limit or 5xx from Anthropic
  3. Rule-based       — caller-supplied fn, or raises ServiceUnavailable

Prompt caching: enabled by default for system prompts. Cache hits cost 10% of normal.
Cost tracking: every call logs token usage. See DOCS/AI-FIRST.md for cost breakdown.

See prompts/registry.py for named, versioned prompts.
"""
import logging
from typing import Any, AsyncIterator, Callable

import anthropic

from config import settings

logger = logging.getLogger(__name__)

_anthropic_client: anthropic.AsyncAnthropic | None = None
_openai_client: Any | None = None  # lazy import


def _get_anthropic() -> anthropic.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _get_openai() -> Any:
    global _openai_client
    if _openai_client is None:
        try:
            from openai import AsyncOpenAI
            _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")
    return _openai_client


async def _anthropic_complete(
    prompt: str,
    system: str,
    model: str,
    max_tokens: int,
    cache_system: bool,
) -> tuple[str, Any]:
    """Returns (text, usage)."""
    client = _get_anthropic()
    system_block = [
        {
            "type": "text",
            "text": system,
            **({"cache_control": {"type": "ephemeral"}} if cache_system else {}),
        }
    ]
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_block,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text, response.usage


async def _openai_complete(
    prompt: str,
    system: str,
    model: str,
    max_tokens: int,
) -> tuple[str, Any]:
    """OpenAI fallback. Model is mapped to closest GPT equivalent."""
    client = _get_openai()

    # Map Claude model names to OpenAI equivalents
    oai_model = "gpt-4o-mini" if "haiku" in model else "gpt-4o"

    response = await client.chat.completions.create(
        model=oai_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content, response.usage


async def complete(
    prompt: str,
    system: str = "You are a helpful assistant.",
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 1024,
    cache_system: bool = True,
    fallback_fn: Callable[[str], str] | None = None,
) -> str:
    """
    Call LLM with automatic provider fallback.

    Provider order: Anthropic → OpenAI → fallback_fn → raises 503.

    Args:
        prompt: user message
        system: system prompt (cached by default — keep it static)
        model: Claude model ID (auto-mapped to OpenAI equivalent on fallback)
        max_tokens: output token limit
        cache_system: enable prompt caching for system prompt (default True)
        fallback_fn: last-resort rule-based function(prompt) -> str
    """
    # Try Anthropic
    if settings.anthropic_api_key:
        try:
            text, usage = await _anthropic_complete(prompt, system, model, max_tokens, cache_system)
            _log_usage(usage, model=model, provider="anthropic")
            return text
        except anthropic.RateLimitError:
            logger.warning("llm.anthropic.rate_limited — trying OpenAI fallback")
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                logger.warning("llm.anthropic.5xx — trying OpenAI fallback", extra={"status": e.status_code})
            else:
                raise

    # Try OpenAI
    if settings.openai_api_key:
        try:
            from openai import RateLimitError as OAIRateLimitError
            text, usage = await _openai_complete(prompt, system, model, max_tokens)
            _log_usage(usage, model=model, provider="openai")
            return text
        except OAIRateLimitError:
            logger.warning("llm.openai.rate_limited — trying rule-based fallback")
        except Exception as e:
            logger.error("llm.openai.error", extra={"error": str(e)})

    # Try rule-based fallback
    if fallback_fn:
        logger.warning("llm.using_rule_based_fallback")
        return fallback_fn(prompt)

    from fastapi import HTTPException
    raise HTTPException(503, "AI generation temporarily unavailable. Please try again shortly.")


async def complete_structured(
    prompt: str,
    schema: type,
    system: str = "You are a helpful assistant.",
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 1024,
    fallback_fn: Callable[[str], Any] | None = None,
) -> Any:
    """
    Call LLM and validate output as a Pydantic model.
    Raises ValueError if the response doesn't match the schema.
    """
    import json

    schema_str = json.dumps(schema.model_json_schema(), indent=2)
    full_prompt = (
        f"{prompt}\n\n"
        f"Respond ONLY with valid JSON matching this schema. No markdown, no explanation:\n"
        f"{schema_str}"
    )

    raw = await complete(full_prompt, system=system, model=model, max_tokens=max_tokens)

    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) >= 2 else raw
    raw = raw.strip()

    try:
        return schema.model_validate_json(raw)
    except Exception as e:
        logger.warning(
            "llm.structured_output.invalid",
            extra={"error": str(e), "raw_preview": raw[:300], "model": model},
        )
        if fallback_fn:
            return fallback_fn(prompt)
        raise ValueError(f"LLM returned invalid structure: {e}")


async def stream(
    prompt: str,
    system: str = "You are a helpful assistant.",
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """
    Stream Claude's response. Falls back to non-streaming OpenAI if Anthropic unavailable.
    Use for generation that takes > 2 seconds to avoid blank-screen UX.
    """
    if settings.anthropic_api_key:
        client = _get_anthropic()
        try:
            async with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            ) as s:
                async for text in s.text_stream:
                    yield text
            return
        except Exception as e:
            logger.warning("llm.stream.anthropic_failed", extra={"error": str(e)})

    # Non-streaming OpenAI fallback for stream endpoints
    text = await complete(prompt, system=system, model=model, max_tokens=max_tokens)
    yield text


def _log_usage(usage: Any, model: str, provider: str) -> None:
    cache_read = getattr(usage, "cache_read_input_tokens", 0)
    cache_creation = getattr(usage, "cache_creation_input_tokens", 0)

    # OpenAI usage object has different attribute names
    if hasattr(usage, "prompt_tokens"):
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        cache_read = 0
        cache_creation = 0
    else:
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens

    regular_input = input_tokens - cache_read - cache_creation

    logger.info(
        "llm.usage",
        extra={
            "provider": provider,
            "model": model,
            "input_tokens": regular_input,
            "cache_creation_tokens": cache_creation,
            "cache_read_tokens": cache_read,
            "output_tokens": output_tokens,
            "cache_savings_pct": round(cache_read / max(input_tokens, 1) * 100),
        },
    )
