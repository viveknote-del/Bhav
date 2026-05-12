"""Single abstraction layer for Claude calls.

HARD RULE: nothing else imports `anthropic` directly. All AI calls flow
through `generate(prompt_name, user_message, ...)`.

How caching works here:
- Each `Prompt` in prompts/registry.py defines a system block + a list of
  (user, assistant) few-shot examples.
- We render `system` as a list-of-blocks and attach `cache_control` to the
  last few-shot example's assistant content. That caches the entire
  prefix (system + examples) in one breakpoint.
- The per-call user message goes at the end and is NOT cached — it varies.
- Bumping `prompt.version` invalidates the cache deliberately (the prefix
  bytes change). That's the whole point of versioning.

Cost tracking:
- Every call logs token usage broken down by input/output/cache_read/
  cache_write, with a $ estimate at Sonnet 4.6 prices.
- Override the model per prompt via `Prompt.model`; default is settings.llm_model.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import anthropic

from config import settings
from prompts import get_prompt
from prompts.base import Prompt

logger = logging.getLogger(__name__)

# Per-1M-token prices. Sonnet 4.6 numbers from Anthropic's published pricing.
# Cache reads = ~0.1× input; cache writes (5-min ephemeral) = ~1.25× input.
_PRICING_PER_1M = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4-7":   {"input": 5.00, "output": 25.00, "cache_read": 0.50, "cache_write": 6.25},
    "claude-haiku-4-5":  {"input": 1.00, "output":  5.00, "cache_read": 0.10, "cache_write": 1.25},
}
_DEFAULT_PRICING = _PRICING_PER_1M["claude-sonnet-4-6"]


# ──────────────────── client lifecycle ──────────────────────

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to .env to enable AI commentary."
            )
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


# ──────────────────── public types ──────────────────────

@dataclass(frozen=True)
class LLMUsage:
    """Token + cost breakdown for a single Claude call."""
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    latency_ms: int

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": self.latency_ms,
        }


@dataclass(frozen=True)
class LLMResult:
    text: str
    usage: LLMUsage


# ──────────────────── message assembly ──────────────────────

def _build_messages(prompt: Prompt, user_message: str) -> list[dict]:
    """Build the messages array with cache_control on the last few-shot example.

    Layout when prompt has N examples:
        [user_1, assistant_1, ..., user_N, assistant_N(cached), user_call]

    The cache marker on assistant_N's content caches everything before it —
    including system + tools (which render before messages per the API).
    """
    msgs: list[dict] = []
    for i, (ex_user, ex_assistant) in enumerate(prompt.examples):
        msgs.append({"role": "user", "content": ex_user})
        is_last = (i == len(prompt.examples) - 1)
        if is_last:
            msgs.append({
                "role": "assistant",
                "content": [
                    {"type": "text", "text": ex_assistant, "cache_control": {"type": "ephemeral"}}
                ],
            })
        else:
            msgs.append({"role": "assistant", "content": ex_assistant})

    msgs.append({"role": "user", "content": user_message})
    return msgs


def _build_system(prompt: Prompt) -> list[dict] | str:
    """Plain string is fine when there are examples — the cache marker on the
    last example caches system+examples together. Only when there are NO
    examples do we cache the system block itself."""
    if not prompt.examples:
        return [{"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}]
    return prompt.system


def _cost_usd(model: str, usage: Any) -> float:
    pricing = _PRICING_PER_1M.get(model, _DEFAULT_PRICING)
    in_tokens = getattr(usage, "input_tokens", 0) or 0
    out_tokens = getattr(usage, "output_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    return (
        in_tokens   * pricing["input"]       / 1_000_000
        + out_tokens  * pricing["output"]      / 1_000_000
        + cache_read  * pricing["cache_read"]  / 1_000_000
        + cache_write * pricing["cache_write"] / 1_000_000
    )


# ──────────────────── public API ──────────────────────

async def generate(prompt_name: str, user_message: str, **overrides) -> LLMResult:
    """Run a prompt against Claude. Returns the text and usage stats.

    `overrides` accepts: model, max_tokens, temperature — useful for evals
    or one-off tweaks. Defaults come from the Prompt in prompts/registry.py
    (and settings.llm_model when the prompt leaves model unset).
    """
    prompt = get_prompt(prompt_name)
    model = overrides.get("model") or prompt.model or settings.llm_model
    max_tokens = overrides.get("max_tokens", prompt.max_tokens)
    temperature = overrides.get("temperature", prompt.temperature)

    client = _get_client()
    messages = _build_messages(prompt, user_message)
    system = _build_system(prompt)

    req_kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }
    if temperature is not None:
        req_kwargs["temperature"] = temperature

    t0 = time.monotonic()
    response = await client.messages.create(**req_kwargs)
    elapsed_ms = round((time.monotonic() - t0) * 1000)

    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")

    usage = LLMUsage(
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cache_read_tokens=response.usage.cache_read_input_tokens or 0,
        cache_write_tokens=response.usage.cache_creation_input_tokens or 0,
        cost_usd=_cost_usd(model, response.usage),
        latency_ms=elapsed_ms,
    )

    logger.info(
        "llm.call",
        extra={
            "prompt": prompt.name,
            "prompt_version": prompt.version,
            "stop_reason": response.stop_reason,
            **usage.as_dict(),
        },
    )

    return LLMResult(text=text.strip(), usage=usage)
