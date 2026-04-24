"""
Single abstraction layer for all LLM calls.
Never call Anthropic/OpenAI SDK directly from routers, services, or workers.
Always go through this module.
"""
from typing import Any

from config import settings


async def complete(
    prompt: str,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 1024,
    system: str | None = None,
) -> str:
    """Call Claude with a prompt. Returns the text response."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    messages = [{"role": "user", "content": prompt}]

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system or "You are a helpful assistant.",
        messages=messages,
    )

    return response.content[0].text


async def complete_structured(
    prompt: str,
    schema: dict[str, Any],
    model: str = "claude-haiku-4-5-20251001",
) -> dict[str, Any]:
    """Call Claude and return a JSON-structured response."""
    import json

    schema_str = json.dumps(schema, indent=2)
    full_prompt = f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{schema_str}"

    raw = await complete(full_prompt, model=model)

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)
