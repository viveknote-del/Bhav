"""Scan orchestration: iterate universe → fetch bars → run detectors → score → persist.

`run_scan(...)` is the entrypoint. Called both inline (tests) and from
the arq worker (`workers/scan_eod.py`). It is responsible for transitioning
the scan_run row from RUNNING to COMPLETED/FAILED.

Bar fetch goes through the daily_bars cache (services/instrument_service.get_chart
already implements cache-first), but for scans we want the freshest bars
possible — so we hit the provider directly and write back to the cache.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

import asyncpg
import pandas as pd

from models.scan import BreakoutOut, ScanDetailOut, ScanRunListOut, ScanRunOut
from providers.market_data import MarketDataProvider
from repositories import bar_repo, breakout_repo, instrument_repo, scan_repo
from services.breakout import _swing_filter
from services.breakout.detectors import DETECTORS
from services.breakout.scoring import score as score_signal
from services.breakout.types import BreakoutSignal

logger = logging.getLogger(__name__)

FETCH_DAYS = 520                 # ~2 years: enough for 252-day 52w lookback + 200d SMA
                                 # backtest needs (so an "as-of N days ago" check has
                                 # the 200d SMA available)
FETCH_CONCURRENCY = 5


# ──────────────────── orchestration ──────────────────────

async def run_scan(
    pool: asyncpg.Pool,
    provider: MarketDataProvider,
    scan_id: UUID,
) -> dict:
    """Run a scan against the active instrument universe. Updates the
    scan_run row to COMPLETED/FAILED. Returns a summary dict the
    worker can store as the job result.
    """
    import time
    t0 = time.monotonic()
    try:
        symbols = await _active_symbols(pool)
        logger.info("scan.start", extra={"scan_id": str(scan_id), "n_symbols": len(symbols)})

        fetch_t0 = time.monotonic()
        scored = await _scan_symbols(pool, provider, symbols)
        fetch_ms = round((time.monotonic() - fetch_t0) * 1000)

        persist_t0 = time.monotonic()
        breakouts_found = await breakout_repo.insert_breakouts(pool, scan_id, scored)
        await scan_repo.complete_scan(pool, scan_id, breakouts_found, datetime.now(timezone.utc))
        persist_ms = round((time.monotonic() - persist_t0) * 1000)

        total_ms = round((time.monotonic() - t0) * 1000)
        logger.info(
            "scan.complete",
            extra={
                "scan_id": str(scan_id),
                "breakouts": breakouts_found,
                "n_symbols": len(symbols),
                "fetch_ms": fetch_ms,
                "persist_ms": persist_ms,
                "total_ms": total_ms,
            },
        )
        return {
            "scan_id": str(scan_id),
            "breakouts_found": breakouts_found,
            "duration_ms": total_ms,
        }

    except Exception as e:                          # noqa: BLE001
        logger.exception(
            "scan.failed",
            extra={"scan_id": str(scan_id), "duration_ms": round((time.monotonic() - t0) * 1000)},
        )
        await scan_repo.fail_scan(pool, scan_id, str(e))
        raise


async def create_and_run_scan(
    pool: asyncpg.Pool,
    provider: MarketDataProvider,
    scan_type: str = "EOD",
) -> UUID:
    """Synchronous variant — useful in tests and for the /v1/scans/_sync route."""
    symbols = await _active_symbols(pool)
    scan_id = await scan_repo.create_scan(pool, scan_type, len(symbols))
    await run_scan(pool, provider, scan_id)
    return scan_id


# ──────────────────── helpers ──────────────────────

async def _active_symbols(pool: asyncpg.Pool) -> list[str]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT symbol FROM instruments WHERE is_active ORDER BY symbol"
        )
    return [r["symbol"] for r in rows]


async def _scan_symbols(
    pool: asyncpg.Pool,
    provider: MarketDataProvider,
    symbols: list[str],
) -> list[tuple[BreakoutSignal, float]]:
    """Batch-fetch all bars in one provider call (`get_bars_many`), then run
    detectors in-process. The batch fetch is the biggest rate-limit win
    against yfinance — one HTTP request per N symbols instead of N requests.
    """
    bars_by_symbol = await provider.get_bars_many(symbols, days=FETCH_DAYS)

    # Persist all fetched bars to the cache in parallel (cheap, all hit local DB).
    await asyncio.gather(*(
        _persist_bars_safe(pool, sym, df) for sym, df in bars_by_symbol.items()
    ))

    n_fetched = len(bars_by_symbol)
    n_missing = len(symbols) - n_fetched
    if n_missing:
        logger.warning(
            "scan.bars_missing",
            extra={"missing": n_missing, "fetched": n_fetched, "total": len(symbols)},
        )

    scored: list[tuple[BreakoutSignal, float]] = []
    swing_rejected: dict[str, int] = {}     # reason → count, for telemetry

    for symbol in symbols:
        bars = bars_by_symbol.get(symbol)
        if bars is None or bars.empty:
            continue

        # Swing-trade pre-gate. If the symbol isn't in an uptrend with
        # strong momentum and trend conviction, skip ALL detectors for it.
        # This is what makes Bhav a swing-trade screener rather than just
        # a "any chart that broke a level" screener.
        gate = _swing_filter.evaluate(bars)
        if not gate.passed:
            swing_rejected[gate.reason or "unknown"] = swing_rejected.get(gate.reason or "unknown", 0) + 1
            continue

        swing_indicators = gate.as_dict()
        for detect in DETECTORS:
            signal = detect(symbol, bars)
            if signal is None:
                continue
            # Enrich the signal's indicators with swing context so the UI
            # can show entry / stop math without re-reading bars.
            enriched_indicators = {**(signal.indicators or {}), **swing_indicators}
            signal = replace(signal, indicators=enriched_indicators)
            composite = score_signal(signal, bars)
            scored.append((signal, composite))

    if swing_rejected:
        logger.info("scan.swing_gate", extra={"rejected": swing_rejected})
    return scored


async def _persist_bars_safe(pool: asyncpg.Pool, symbol: str, df: pd.DataFrame) -> None:
    try:
        await bar_repo.upsert_bars(pool, symbol, df)
    except Exception as e:                                    # noqa: BLE001
        logger.warning("scan.cache_write_failed", extra={"symbol": symbol, "error": str(e)})


async def _get_fresh_bars(
    pool: asyncpg.Pool,
    provider: MarketDataProvider,
    symbol: str,
) -> pd.DataFrame:
    """Fetch from provider, persist to cache, return DataFrame.

    For scans we always hit the provider for the latest bars — detectors
    fire on today's close, so a stale cache would mean missed signals.
    """
    try:
        df = await provider.get_bars(symbol, days=FETCH_DAYS)
    except Exception as e:
        logger.warning("scan.fetch_failed", extra={"symbol": symbol, "error": str(e)})
        return pd.DataFrame()
    if not df.empty:
        try:
            await bar_repo.upsert_bars(pool, symbol, df)
        except Exception as e:
            logger.warning("scan.cache_write_failed", extra={"symbol": symbol, "error": str(e)})
    return df


# ──────────────────── read API ──────────────────────

def _scan_record_to_model(row: asyncpg.Record) -> ScanRunOut:
    return ScanRunOut(
        id=row["id"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        scan_type=row["scan_type"],
        universe_size=row["universe_size"],
        breakouts_found=row["breakouts_found"],
        status=row["status"],
        error=row["error"],
        summary=row["summary"],
    )


def _breakout_record_to_model(row: asyncpg.Record) -> BreakoutOut:
    return BreakoutOut(
        id=row["id"],
        scan_run_id=row["scan_run_id"],
        symbol=row["symbol"],
        detected_at=row["detected_at"],
        breakout_type=row["breakout_type"],
        pattern_subtype=row["pattern_subtype"],
        price=float(row["price"]),
        breakout_level=float(row["breakout_level"]) if row["breakout_level"] is not None else None,
        volume_ratio=float(row["volume_ratio"]) if row["volume_ratio"] is not None else None,
        composite_score=float(row["composite_score"]),
        indicators=_load_jsonb(row["indicators"]),
        ai_commentary=row["ai_commentary"],
        news_links=_load_jsonb(row["news_links"]),
    )


def _load_jsonb(val) -> dict | list | None:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    return json.loads(val)


async def list_scans(pool: asyncpg.Pool, page: int, limit: int) -> ScanRunListOut:
    page = max(1, page)
    limit = max(1, min(limit, 200))
    rows, total = await scan_repo.list_scans(pool, limit=limit, offset=(page - 1) * limit)
    return ScanRunListOut(
        items=[_scan_record_to_model(r) for r in rows],
        total=total,
        page=page,
        limit=limit,
    )


async def get_scan_detail(pool: asyncpg.Pool, scan_id: UUID) -> ScanDetailOut | None:
    scan_row = await scan_repo.get_scan(pool, scan_id)
    if scan_row is None:
        return None
    breakout_rows, _ = await breakout_repo.list_breakouts(pool, scan_run_id=scan_id, limit=200)
    return ScanDetailOut(
        scan=_scan_record_to_model(scan_row),
        breakouts=[_breakout_record_to_model(r) for r in breakout_rows],
    )
