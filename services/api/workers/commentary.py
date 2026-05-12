"""Commentary worker — runs after scan_eod completes.

One job covers per-breakout commentary for the top N (cost-bounded by
settings.commentary_top_n) and the once-per-scan EOD digest.
"""
from __future__ import annotations

import logging
from uuid import UUID

from services import alert_service, commentary_service
from workers.base import job

logger = logging.getLogger(__name__)


@job(name="commentary_for_scan", max_retries=2)
async def commentary_for_scan(ctx: dict, scan_id: str) -> dict:
    pool = ctx["pool"]
    scan_uuid = UUID(scan_id)
    commented = await commentary_service.generate_for_top_n(pool, scan_uuid)
    digest = await commentary_service.generate_eod_digest(pool, scan_uuid)
    # Telegram alerts on high-conviction breakouts (no-op if not configured)
    alerted = await alert_service.evaluate_and_alert(pool, scan_uuid)
    return {
        "scan_id": scan_id,
        "commented": commented,
        "digest_written": digest is not None,
        "alerted": alerted,
    }


@job(name="commentary_for_breakout", max_retries=2)
async def commentary_for_breakout(ctx: dict, breakout_id: str) -> dict:
    pool = ctx["pool"]
    text = await commentary_service.generate_for_breakout(pool, UUID(breakout_id))
    return {"breakout_id": breakout_id, "length": len(text)}
