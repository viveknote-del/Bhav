"""arq WorkerSettings entry point.

Run with: `arq workers.WorkerSettings` from services/api/.
The worker process opens its own asyncpg pool (separate from the API's)
and shares the Redis broker with the API.

Cron jobs run on the worker's clock. We schedule in UTC and let the job
itself check Indian-market hours/holidays:
- EOD scan: 10:05 UTC Mon-Fri (= 15:35 IST). The job checks for NSE
  holidays before running.
- Intraday: every 5 min; the job no-ops outside market hours or when
  INTRADAY_ENABLED=false.
"""
from __future__ import annotations

import logging

from arq import cron

from arq_client import redis_settings
from db import open_pool
from workers.commentary import commentary_for_breakout, commentary_for_scan
from workers.cron import eod_scan_cron, intraday_scan_cron
from workers.scan_eod import scan_eod

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    ctx["pool"] = await open_pool()
    logger.info(
        "worker.startup",
        extra={"jobs": ["scan_eod", "commentary_for_scan", "commentary_for_breakout"]},
    )


async def shutdown(ctx: dict) -> None:
    pool = ctx.get("pool")
    if pool is not None:
        await pool.close()
    logger.info("worker.shutdown")


class WorkerSettings:
    functions = [scan_eod, commentary_for_scan, commentary_for_breakout]
    cron_jobs = [
        cron(eod_scan_cron, hour=10, minute=5, weekday={"mon", "tue", "wed", "thu", "fri"}, unique=True),
        # Intraday loop fires every 5 min year-round; the job no-ops outside market hours.
        cron(intraday_scan_cron, minute=set(range(0, 60, 5)), unique=True),
    ]
    redis_settings = redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    keep_result = 3600              # keep job_results in Redis for 1h
    max_jobs = 4
