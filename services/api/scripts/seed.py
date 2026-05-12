"""Seed the instruments table with the NIFTY 50 universe.

Usage:
    python -m scripts.seed              # offline (no provider call)
    python -m scripts.seed --refresh    # offline seed + fetch metadata from provider
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from db import open_pool
from providers.factory import get_market_data_provider
from services import instrument_service


async def _main(refresh: bool) -> int:
    pool = await open_pool()
    try:
        if refresh:
            print("Seeding offline + refreshing from provider...")
            await instrument_service.seed_universe_offline(pool)
            provider = get_market_data_provider()
            result = await instrument_service.refresh_universe(pool, provider)
        else:
            print("Seeding offline (no provider call)...")
            result = await instrument_service.seed_universe_offline(pool)

        print(f"Inserted: {result.inserted}  Updated: {result.updated}  Failed: {len(result.failed)}")
        if result.failed:
            print("Failed symbols:", ", ".join(result.failed))
        return 0
    finally:
        await pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="After seeding, fetch fresh metadata from the market data provider.")
    args = parser.parse_args()
    sys.exit(asyncio.run(_main(refresh=args.refresh)))
