"""Prompt as first-class code.

Every AI prompt lives here — never inline strings in services. Enables
versioning, eval testing, model targeting, and centralized swaps. Bumping
`version` is a deliberate, cache-invalidating change (the prefix bytes
change, so the next call writes a new cache entry).

Few-shot examples live on the Prompt and become message-history turns so
that the entire system + examples block is cacheable. See providers/llm.py
for how they're assembled into a request.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalCase:
    """One test case. Runs during CI to catch prompt quality regressions."""
    input: str
    must_contain: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)
    min_length: int = 10
    max_length: int | None = None
    description: str = ""


@dataclass
class Prompt:
    """A versioned, testable prompt definition.

    `examples` are (user_input, assistant_output) pairs. They render into
    the conversation as alternating user/assistant turns; the LLM provider
    places the cache breakpoint on the last example so system + examples
    cache together as one prefix.
    """
    name: str
    version: str
    system: str
    examples: list[tuple[str, str]] = field(default_factory=list)
    model: str | None = None              # falls back to settings.llm_model
    max_tokens: int = 1024
    temperature: float | None = None
    eval_cases: list[EvalCase] = field(default_factory=list)
    notes: str = ""
