# AI-First Development Guide

Reference doc — read when designing AI features or optimizing session token usage. NOT auto-loaded.

---

## Session token strategy

### The CLAUDE.md problem

CLAUDE.md loads on **every** Claude Code session. Every 100 lines ≈ 2,500 tokens — burned before you type a single word.

| File | Cost | Rule |
|---|---|---|
| CLAUDE.md | Loads every session | Hard limit: 300 lines. Archive aggressively. |
| DOCS/*.md trackers | Loaded by commands | Keep only active items. Archive completed. |
| `DOCS/pipeline/step-*/summary.md` | Loaded by pipeline Phase 0 | These ARE the AI's cross-session memory — keep them |
| Source files | Read on demand | Fine to grow naturally |

### What eats tokens without value

- Resolved bugs still in `BUGS.md` — they're done, archive them
- Completed KANBAN tasks still in the active board — archive them
- Old session logs baked into CLAUDE.md — this is what caused the 146KB bloat in TixReady
- Repeating architecture facts that are already in `ARCHITECTURE.md`

### What saves tokens without losing context

- `DOCS/pipeline/step-N/summary.md` — 1 file per completed step, ~50 lines, replaces re-reading the entire codebase
- `ARCHITECTURE.md` — always current, agents update it during Phase 7
- `DOCS/DECISIONS.md` — why choices were made; prevents re-litigating them

Run `/trim` periodically (every 3-5 merged PRs) to archive and keep things lean.

---

## Model routing guide

Pick the right model for the task. Wrong picks are the #1 source of unnecessary cost.

| Task type | Model | Why |
|---|---|---|
| Design, architecture, requirements | opus | Catches edge cases haiku misses; wrong design costs hours |
| Code review, security audit | opus | Same — subtle bugs are expensive |
| Routine CRUD (endpoints, migrations, models) | haiku | Handles these perfectly at 1/20th the cost |
| Fixing a failing test | opus first pass | Diagnosis requires reasoning; haiku loops |
| Writing docs, summaries | sonnet | Good quality without opus cost |
| Context loading, file reads | sonnet | No reasoning needed |
| Simple refactor (rename, extract) | haiku | Mechanical transformation |
| E2E test generation | haiku | Template-like work |

**The escalation rule:** Start haiku. Escalate to opus only when haiku fails (test failure, build error, second pass needed). This cuts pipeline cost ~75% while maintaining quality.

---

## Prompt caching in your app

If your app makes repeated LLM calls with the same system prompt, cache it. This is a first-class feature in the Claude API.

### When to cache

- ✅ System prompt is the same across calls (almost always true for workers)
- ✅ System prompt is long (> 1,024 tokens — below this there's no benefit)
- ✅ Called more than 5-10 times (cache TTL is 5 minutes; subsequent calls within TTL get 90% discount)
- ❌ System prompt changes every call (dynamic user content in system — move it to user turn)

### How to structure prompts for caching

```python
# CORRECT — static system prompt, dynamic user content
system = """
You are a marketing copywriter specializing in event promotion.
You write engaging, concise captions for Instagram.
[... 500 more tokens of static context ...]
"""  # ← this gets cached

user_prompt = f"""
Write a caption for this event:
Name: {event.name}
Date: {event.date}
Vibe: {event.vibe}
"""  # ← this varies per call, not cached

# WRONG — dynamic content baked into system prompt (defeats caching)
system = f"You are a copywriter. The event is {event.name} on {event.date}."
```

### Cache hit economics

| Model | Input token cost | Cached token cost | Savings |
|---|---|---|---|
| Haiku | $0.25/M | $0.025/M | 90% |
| Sonnet | $3.00/M | $0.30/M | 90% |
| Opus | $15.00/M | $1.50/M | 90% |

A 2,000-token system prompt called 1,000 times/day: **$0.50/day cached vs $5.00/day uncached**.

---

## Human-in-the-loop patterns

Not all AI actions should be automatic. Use this decision matrix:

| Action | Reversible? | Cost if wrong | Pattern |
|---|---|---|---|
| Generate draft copy | Yes | Low | Auto-generate, let user edit |
| Publish to social media | No | High | Generate → human review → publish |
| Send emails to guests | No | High | Generate → human approve → send |
| Update DB records | Partially | Medium | Auto + audit log |
| Delete content | No | High | Always require human confirmation |

### Approval queue pattern

For high-stakes AI actions, enqueue them for human review before execution:

```python
# Instead of publishing directly:
await repo.create_pending_action(
    type="publish_post",
    payload={"post_id": post_id, "caption": ai_caption},
    status="PENDING_REVIEW",
)

# Frontend shows a review queue; human clicks Approve → triggers execution
```

---

## Streaming responses

For long-running generation (copy, images), stream the response rather than blocking:

```python
# providers/llm.py — streaming variant
async def stream_complete(prompt: str, system: str):
    async with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
```

```python
# router — SSE endpoint
from fastapi.responses import StreamingResponse

@router.post("/campaigns/{id}/generate-copy")
async def generate_copy_stream(id: str, user: dict = Depends(require_user)):
    campaign = await get_campaign_or_404(id, user["sub"])
    
    async def event_stream():
        async for chunk in llm.stream_complete(build_prompt(campaign), COPY_SYSTEM_PROMPT):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

Use streaming when generation takes > 2 seconds. Users experience latency as responsiveness when they see text appearing.

---

## Cost tracking

Add a middleware or decorator to log token usage per endpoint:

```python
# After every LLM call in providers/llm.py
logger.info(
    "llm.call",
    extra={
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_read_tokens": getattr(response.usage, "cache_read_input_tokens", 0),
        "cache_creation_tokens": getattr(response.usage, "cache_creation_input_tokens", 0),
        "endpoint": ctx.get("endpoint"),
    }
)
```

This gives you a log-based cost dashboard without any third-party tooling.

---

## Evals workflow

Evals are the test suite for your AI quality. Run them the same way you run `pytest`.

```
Prompt changes without evals = merging untested code.
```

### Day-to-day workflow

```bash
# 1. Change a prompt in prompts/registry.py
# 2. Bump the version string
# 3. Run evals locally
make evals

# 4. If a case fails, either:
#    a. Fix the prompt (it regressed)
#    b. Update the eval case (the criteria were wrong)
# 5. Commit — CI re-runs evals automatically on the PR
```

### When to add eval cases

- Every new prompt gets at least 2 eval cases before merging
- When a user reports bad output → add an eval case that catches that exact failure, then fix the prompt
- When you upgrade model versions → run evals first, check for regressions

### LLM-as-judge (advanced)

For outputs that are hard to check with substring matching (creative writing, summaries), use a cheaper model to judge the output:

```python
EvalCase(
    description="Caption is engaging and under 150 chars",
    input="Summer music festival, indie bands, outdoor venue",
    # Use a judge prompt instead of must_contain
    judge_prompt="Is this caption engaging and under 150 characters? Reply YES or NO.",
    judge_must_contain=["YES"],
)
```
Add a `judge_prompt` field to `EvalCase` and a `_run_judge()` helper in `evals/runner.py` when you need this.

---

## Multi-provider fallback

The current fallback chain in `providers/llm.py`:

```
Anthropic (primary)
  → RateLimitError or 5xx?
OpenAI (fallback)
  → RateLimitError?
fallback_fn (caller-supplied rule-based function)
  → no fallback_fn?
503 ServiceUnavailable
```

**When to supply a `fallback_fn`:** Any user-facing feature where a broken response is better than a 503. Example: if copy generation fails, return a template string with the event name filled in. The user gets something, not an error screen.

```python
def _template_copy(prompt: str) -> str:
    return "Join us for an unforgettable event. Limited spots available."

result = await llm.complete(
    prompt,
    system=SYSTEM_PROMPT,
    fallback_fn=_template_copy,
)
```
