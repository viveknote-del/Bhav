"""
Per-user AI cost budget enforcement.

Tracks cumulative token usage per user per day via Redis.
Returns 429 when a user exceeds their daily token budget.

Budget tiers (set in config.py):
  free:       100,000 input tokens/day  (~$0.025 on Haiku)
  growth:     500,000 input tokens/day
  pro:      2,000,000 input tokens/day

Wire into providers/llm.py — call record_usage() after every LLM call.
Call check_budget() at the start of any AI endpoint.

This is service-level, not HTTP middleware, because only AI endpoints
need checking — checking every HTTP request would be wasteful.
"""
import logging
from datetime import date

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

DAILY_LIMITS: dict[str, int] = {
    "free": 100_000,
    "growth": 500_000,
    "pro": 2_000_000,
}


def _budget_key(user_id: str) -> str:
    today = date.today().isoformat()
    return f"ai_budget:{user_id}:{today}"


async def get_usage(user_id: str, redis: Redis) -> int:
    """Return how many tokens this user has used today."""
    val = await redis.get(_budget_key(user_id))
    return int(val) if val else 0


async def record_usage(user_id: str, tokens_used: int, redis: Redis) -> int:
    """
    Increment user's daily token counter. Call this after every LLM completion.
    Returns the new cumulative total.
    Sets TTL to 25 hours so keys expire naturally after the day rolls over.
    """
    key = _budget_key(user_id)
    new_total = await redis.incrby(key, tokens_used)
    await redis.expire(key, 90_000)  # 25 hours
    return new_total


async def check_budget(user_id: str, tier: str, redis: Redis) -> None:
    """
    Raise BudgetExceededError if user is over their daily limit.
    Call at the start of any endpoint that triggers LLM calls.

    Example usage in a router:
        await cost_budget.check_budget(user["sub"], user.get("tier", "free"), redis)
    """
    limit = DAILY_LIMITS.get(tier, DAILY_LIMITS["free"])
    used = await get_usage(user_id, redis)

    if used >= limit:
        logger.warning(
            "cost_budget.exceeded",
            extra={"user_id": user_id, "tier": tier, "used": used, "limit": limit},
        )
        from fastapi import HTTPException
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_ai_limit_reached",
                "message": f"You've used {used:,} tokens today (limit: {limit:,}). Resets at midnight UTC.",
                "used": used,
                "limit": limit,
                "tier": tier,
            },
        )

    logger.debug(
        "cost_budget.ok",
        extra={"user_id": user_id, "used": used, "limit": limit, "remaining": limit - used},
    )
