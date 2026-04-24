"""
Central registry of all prompts.

Add a new prompt: define it below and add it to REGISTRY.
The eval runner discovers all prompts through this registry.
"""
from .base import EvalCase, Prompt

# ---------------------------------------------------------------------------
# Prompt definitions
# ---------------------------------------------------------------------------

EXAMPLE_ASSISTANT = Prompt(
    name="example_assistant",
    version="1.0",
    model="claude-haiku-4-5-20251001",
    max_tokens=512,
    system="""You are a helpful assistant for {{PROJECT_DISPLAY_NAME}}.
Be concise, friendly, and accurate. Never make up information.
If you don't know something, say so clearly.""",
    eval_cases=[
        EvalCase(
            description="Responds helpfully to a greeting",
            input="Hello, how are you?",
            must_contain=[],
            must_not_contain=["I cannot", "I am unable"],
            min_length=10,
        ),
        EvalCase(
            description="Admits uncertainty rather than hallucinating",
            input="What is the current stock price of AAPL?",
            must_contain=["don't know", "cannot", "real-time", "current"],
            min_length=10,
        ),
    ],
    notes="Base assistant prompt. Keep it short — this is cached and loaded often.",
)

# ---------------------------------------------------------------------------
# Registry — add every prompt here
# ---------------------------------------------------------------------------

REGISTRY: dict[str, Prompt] = {
    "example_assistant": EXAMPLE_ASSISTANT,
}


def get_prompt(name: str) -> Prompt:
    if name not in REGISTRY:
        raise KeyError(f"Prompt '{name}' not found. Available: {list(REGISTRY.keys())}")
    return REGISTRY[name]


def list_prompts() -> list[Prompt]:
    return list(REGISTRY.values())
