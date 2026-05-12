"""arq WorkerSettings entry point.

Run with: `arq workers.WorkerSettings` from services/api/.
The worker process opens its own asyncpg pool (separate from the API's)
and shares the Redis broker with the API.
"""
from __future__ import annotations

import logging

from arq_client import redis_settings
from db import open_pool
from workers.scan_eod import scan_eod

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    ctx["pool"] = await open_pool()
    logger.info("worker.startup", extra={"jobs": [scan_eod.__name__]})


async def shutdown(ctx: dict) -> None:
    pool = ctx.get("pool")
    if pool is not None:
        await pool.close()
    logger.info("worker.shutdown")


class WorkerSettings:
    functions = [scan_eod]
    redis_settings = redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    keep_result = 3600              # keep job_results in Redis for 1h
    max_jobs = 4
