"""EOD scan worker — runs detectors, then enqueues commentary for the
scan's top-N breakouts.

The arq context provides `ctx['redis']` (an ArqRedis pool), which we use
to enqueue the follow-up commentary job. Splitting commentary into its
own job means a transient Claude/NewsAPI failure doesn't poison the
scan itself.
"""
from __future__ import annotations

import logging
from uuid import UUID

from providers.factory import get_market_data_provider
from services import scan_service
from workers.base import job

logger = logging.getLogger(__name__)


@job(name="scan_eod", max_retries=2)
async def scan_eod(ctx: dict, scan_id: str) -> dict:
    pool = ctx["pool"]
    provider = get_market_data_provider()
    result = await scan_service.run_scan(pool, provider, UUID(scan_id))

    # Enqueue commentary as a separate job so scan success isn't tied to AI uptime.
    redis = ctx.get("redis")
    if redis is not None and result.get("breakouts_found", 0) > 0:
        try:
            await redis.enqueue_job("commentary_for_scan", scan_id)
            logger.info("scan.commentary_enqueued", extra={"scan_id": scan_id})
        except Exception as e:                          # noqa: BLE001
            logger.warning("scan.commentary_enqueue_failed", extra={"scan_id": scan_id, "error": str(e)})

    return result
