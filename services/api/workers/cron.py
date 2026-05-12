"""Scheduled scan jobs.

The arq cron schedule lives in workers/__init__.py — these are the
implementations. Each cron job is responsible for checking that today
is actually a trading day before doing any work; the cron times are in
UTC and Indian markets close on weekends + holidays.
"""
from __future__ import annotations

import logging

from config import settings
from market_hours import is_market_open, is_trading_day, now_ist
from providers.factory import get_market_data_provider
from services import scan_service

logger = logging.getLogger(__name__)


async def eod_scan_cron(ctx: dict) -> dict | None:
    """Runs every weekday at 10:05 UTC (15:35 IST). Skips holidays."""
    today_ist = now_ist().date()
    if not is_trading_day(today_ist):
        logger.info("cron.eod.skipped", extra={"date": today_ist.isoformat(), "reason": "not_trading_day"})
        return {"skipped": True, "reason": "not_trading_day"}

    pool = ctx["pool"]
    provider = get_market_data_provider()
    scan_id = await scan_service.create_and_run_scan(pool, provider, scan_type="EOD")
    logger.info("cron.eod.completed", extra={"scan_id": str(scan_id), "date": today_ist.isoformat()})

    # Enqueue commentary follow-up (same handoff scan_eod.py uses)
    redis = ctx.get("redis")
    if redis is not None:
        try:
            await redis.enqueue_job("commentary_for_scan", str(scan_id))
        except Exception as e:                          # noqa: BLE001
            logger.warning("cron.eod.commentary_enqueue_failed", extra={"scan_id": str(scan_id), "error": str(e)})

    return {"scan_id": str(scan_id)}


async def intraday_scan_cron(ctx: dict) -> dict | None:
    """Runs every 5 minutes. Gated by INTRADAY_ENABLED env + market hours."""
    if not settings.intraday_enabled:
        return None
    if not is_market_open():
        return None

    pool = ctx["pool"]
    provider = get_market_data_provider()
    scan_id = await scan_service.create_and_run_scan(pool, provider, scan_type="INTRADAY")
    logger.info("cron.intraday.completed", extra={"scan_id": str(scan_id)})

    redis = ctx.get("redis")
    if redis is not None:
        try:
            await redis.enqueue_job("commentary_for_scan", str(scan_id))
        except Exception as e:                          # noqa: BLE001
            logger.warning("cron.intraday.commentary_enqueue_failed", extra={"scan_id": str(scan_id), "error": str(e)})

    return {"scan_id": str(scan_id)}
