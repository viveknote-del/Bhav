"""
Prompt as first-class code.

Every AI prompt in this app lives here — not as inline strings in services.
This enables: versioning, eval testing, model targeting, and centralized swaps.

Usage:
    from prompts import get_prompt
    prompt = get_prompt("copy_writer")
    result = await llm.complete(user_input, system=prompt.system, model=prompt.model)
"""
from dataclasses import dataclass, field


@dataclass
class EvalCase:
    """One test case for a prompt. Runs during CI to catch quality regressions."""
    input: str
    must_contain: list[str] = field(default_factory=list)  # substrings that must appear
    must_not_contain: list[str] = field(default_factory=list)  # substrings that must NOT appear
    min_length: int = 10
    max_length: int | None = None
    description: str = ""


@dataclass
class Prompt:
    """A versioned, testable prompt definition."""
    name: str
    version: str
    system: str
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 1024
    eval_cases: list[EvalCase] = field(default_factory=list)
    notes: str = ""  # why this prompt exists / key design decisions
