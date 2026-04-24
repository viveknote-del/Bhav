"""
Single abstraction layer for all LLM calls.

HARD RULE: Never import anthropic/openai directly from routers, services, or workers.
All AI calls go through this module. Benefits:
  - Model swaps happen in one place
  - Prompt caching is automatic for system prompts
  - Retry logic is centralized
  - Cost tracking logs from one place

See DOCS/AI-FIRST.md for caching strategy and cost breakdown.
"""
import logging
from typing import Any, AsyncIterator

import anthropic

from config import settings

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def complete(
    prompt: str,
    system: str = "You are a helpful assistant.",
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 1024,
    cache_system: bool = True,
) -> str:
    """
    Call Claude and return the text response.

    Set cache_system=True (default) to cache the system prompt.
    Cache hits cost 10% of normal input tokens — always cache unless the
    system prompt changes every call (rare).

    Cache TTL is 5 minutes. Calls within the window share the cache.
    Minimum cacheable block: 1,024 tokens for Haiku/Sonnet, 2,048 for Opus.
    Below those thresholds, cache_system has no effect.
    """
    client = _get_client()

    system_block: list[dict] = [
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

    _log_usage(response.usage, model=model)

    return response.content[0].text


async def complete_structured(
    prompt: str,
    schema: type,  # Pydantic BaseModel subclass
    system: str = "You are a helpful assistant.",
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 1024,
) -> Any:
    """
    Call Claude and parse the response into a Pydantic model.

    Always validates with Pydantic — never returns raw strings.
    Raises ValueError if the LLM returns invalid JSON or schema mismatch.
    """
    import json

    schema_str = json.dumps(schema.model_json_schema(), indent=2)
    full_prompt = (
        f"{prompt}\n\n"
        f"Respond ONLY with valid JSON matching this schema. No markdown, no explanation:\n"
        f"{schema_str}"
    )

    raw = await complete(full_prompt, system=system, model=model, max_tokens=max_tokens)

    # Strip markdown code fences if model adds them
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) >= 2 else raw

    try:
        return schema.model_validate_json(raw)
    except Exception as e:
        logger.warning(
            "llm.structured_output.invalid",
            extra={"error": str(e), "raw_preview": raw[:300], "model": model},
        )
        raise ValueError(f"LLM returned invalid structure: {e}")


async def stream(
    prompt: str,
    system: str = "You are a helpful assistant.",
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """
    Stream Claude's response chunk by chunk.

    Use this for generation that takes > 2 seconds — users experience
    latency as responsiveness when they see text appearing.

    Usage in a FastAPI SSE endpoint:
        async def event_stream():
            async for chunk in llm.stream(prompt, system):
                yield f"data: {chunk}\\n\\n"
            yield "data: [DONE]\\n\\n"
        return StreamingResponse(event_stream(), media_type="text/event-stream")
    """
    client = _get_client()

    async with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as s:
        async for text in s.text_stream:
            yield text


def _log_usage(usage: Any, model: str) -> None:
    """Log token usage for cost tracking. Aggregate these logs for a cost dashboard."""
    cache_read = getattr(usage, "cache_read_input_tokens", 0)
    cache_creation = getattr(usage, "cache_creation_input_tokens", 0)
    regular_input = usage.input_tokens - cache_read - cache_creation

    logger.info(
        "llm.usage",
        extra={
            "model": model,
            "input_tokens": regular_input,
            "cache_creation_tokens": cache_creation,
            "cache_read_tokens": cache_read,
            "output_tokens": usage.output_tokens,
            "cache_savings_pct": round(cache_read / max(usage.input_tokens, 1) * 100),
        },
    )
