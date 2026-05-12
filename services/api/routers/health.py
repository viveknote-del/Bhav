from __future__ import annotations

import asyncio
import logging
import time
from typing import Annotated

import asyncpg
import redis.asyncio as redis_lib
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from config import settings
from db import get_pool

router = APIRouter(prefix="/v1/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("")
async def health_check(pool: Annotated[asyncpg.Pool, Depends(get_pool)]):
    """200 if DB and Redis reachable; 503 if either is down."""
    checks: dict[str, dict] = {}
    overall = "ok"

    t0 = time.monotonic()
    try:
        async with pool.acquire() as conn:
            await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=2.0)
        checks["database"] = {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)[:200]}
        overall = "degraded"
        logger.error("health.database.failed", extra={"error": str(e)})

    t0 = time.monotonic()
    try:
        r = redis_lib.from_url(settings.redis_url, socket_timeout=2)
        await r.ping()
        await r.close()
        checks["redis"] = {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)[:200]}
        overall = "degraded"
        logger.error("health.redis.failed", extra={"error": str(e)})

    checks["ai_provider"] = {
        "status": "configured" if settings.anthropic_api_key else "unconfigured",
        "model": settings.llm_model,
    }
    checks["market_data"] = {"provider": settings.market_data_provider}

    status_code = 200 if overall == "ok" else 503
    return JSONResponse({"status": overall, "checks": checks}, status_code=status_code)


@router.get("/ping")
async def ping():
    """Minimal liveness probe — no dependency checks."""
    return {"status": "ok"}
