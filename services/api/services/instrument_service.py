"""Business logic for instruments and bars.

Reads happen cache-first against `daily_bars`; if the cache is stale we
hit the provider and upsert the new bars before returning. The seeder
also lives here so the refresh endpoint and CLI seed share one path.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

import asyncpg
import pandas as pd

from data.nifty_50 import NIFTY_50
from models.instrument import Bar, ChartOut, InstrumentListOut, InstrumentOut, RefreshResult
from providers.market_data import MarketDataProvider
from repositories import bar_repo, instrument_repo

logger = logging.getLogger(__name__)

# yfinance fetches in parallel, but we throttle to avoid 429s on free tier
_FETCH_CONCURRENCY = 5
# Re-fetch from yfinance if the latest cached bar is older than this many days
_BAR_STALENESS_DAYS = 1


def _record_to_instrument(row: asyncpg.Record) -> InstrumentOut:
    return InstrumentOut(
        symbol=row["symbol"],
        exchange=row["exchange"],
        name=row["name"],
        sector=row["sector"],
        industry=row["industry"],
        market_cap=float(row["market_cap"]) if row["market_cap"] is not None else None,
        is_active=row["is_active"],
        updated_at=row["updated_at"],
    )


async def list_instruments(
    pool: asyncpg.Pool,
    exchange: str | None,
    search: str | None,
    page: int,
    limit: int,
) -> InstrumentListOut:
    page = max(1, page)
    limit = max(1, min(limit, 200))
    offset = (page - 1) * limit
    rows, total = await instrument_repo.list_instruments(
        pool, exchange=exchange, search=search, limit=limit, offset=offset
    )
    return InstrumentListOut(
        items=[_record_to_instrument(r) for r in rows],
        total=total,
        page=page,
        limit=limit,
    )


async def get_chart(
    pool: asyncpg.Pool,
    provider: MarketDataProvider,
    symbol: str,
    days: int,
) -> ChartOut | None:
    """Cache-first chart fetch. Refreshes from provider if cache is stale."""
    inst = await instrument_repo.get_instrument(pool, symbol)
    if inst is None:
        return None

    latest = await bar_repo.latest_bar_date(pool, symbol)
    needs_refresh = (
        latest is None or (date.today() - latest) > timedelta(days=_BAR_STALENESS_DAYS)
    )
    if needs_refresh:
        df = await provider.get_bars(symbol, days=max(days, 250))
        if not df.empty:
            await bar_repo.upsert_bars(pool, symbol, df)

    bars_df = await bar_repo.get_bars(pool, symbol, days=days)
    bars = [
        Bar(
            date=ts.date() if isinstance(ts, pd.Timestamp) else ts,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
        )
        for ts, row in bars_df.iterrows()
    ]
    return ChartOut(symbol=symbol, bars=bars)


async def refresh_universe(
    pool: asyncpg.Pool, provider: MarketDataProvider
) -> RefreshResult:
    """Upsert NIFTY 50 with fresh metadata from the provider.

    Symbol + name + sector come from the bundled seed; market_cap (and
    any missing sector/industry) is filled from the provider.
    """
    sem = asyncio.Semaphore(_FETCH_CONCURRENCY)

    async def _one(entry: dict) -> tuple[str, str | None, dict | None]:
        async with sem:
            try:
                info = await provider.get_instrument_info(entry["symbol"])
                return entry["symbol"], None, info.__dict__ if info else None
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "refresh.fetch_failed",
                    extra={"symbol": entry["symbol"], "error": str(e)},
                )
                return entry["symbol"], str(e), None

    results = await asyncio.gather(*(_one(e) for e in NIFTY_50))

    inserted = 0
    updated = 0
    failed: list[str] = []
    for entry, (symbol, err, info) in zip(NIFTY_50, results):
        if err:
            failed.append(symbol)
            continue
        sector = (info or {}).get("sector") or entry.get("sector")
        industry = (info or {}).get("industry")
        market_cap = (info or {}).get("market_cap")
        action = await instrument_repo.upsert_instrument(
            pool,
            symbol=entry["symbol"],
            exchange="NSE",
            name=(info or {}).get("name") or entry["name"],
            sector=sector,
            industry=industry,
            market_cap=market_cap,
        )
        if action == "inserted":
            inserted += 1
        else:
            updated += 1

    return RefreshResult(inserted=inserted, updated=updated, failed=failed)


async def seed_universe_offline(pool: asyncpg.Pool) -> RefreshResult:
    """Seed instruments from the static NIFTY 50 list without calling
    the provider — used for first-time setup or when offline. Market cap
    is left null and will be filled by a later refresh."""
    inserted = 0
    updated = 0
    for entry in NIFTY_50:
        action = await instrument_repo.upsert_instrument(
            pool,
            symbol=entry["symbol"],
            exchange="NSE",
            name=entry["name"],
            sector=entry.get("sector"),
            industry=None,
            market_cap=None,
        )
        if action == "inserted":
            inserted += 1
        else:
            updated += 1
    return RefreshResult(inserted=inserted, updated=updated, failed=[])
