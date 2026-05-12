"""EOD scan worker — runs detectors over the active universe."""
from __future__ import annotations

import logging
from uuid import UUID

from providers.factory import get_market_data_provider
from services import scan_service
from workers.base import job

logger = logging.getLogger(__name__)


@job(name="scan_eod", max_retries=2)
async def scan_eod(ctx: dict, scan_id: str) -> dict:
    """Run a full EOD scan, persisting breakouts under `scan_id`."""
    pool = ctx["pool"]
    provider = get_market_data_provider()
    return await scan_service.run_scan(pool, provider, UUID(scan_id))
