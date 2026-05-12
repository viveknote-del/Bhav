"""Raw asyncpg queries for `daily_bars`. Caching layer between yfinance
and detectors — detectors read bars exclusively through the service,
which checks the cache before calling the provider.
"""
from __future__ import annotations

from datetime import date

import asyncpg
import pandas as pd


async def get_bars(
    pool: asyncpg.Pool, symbol: str, days: int
) -> pd.DataFrame:
    """Return cached bars (most recent `days` trading days) as a DataFrame.

    Index is DatetimeIndex; columns are open, high, low, close, volume.
    Empty DataFrame if nothing cached.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT date, open, high, low, close, volume
              FROM daily_bars
             WHERE symbol = $1
             ORDER BY date DESC
             LIMIT $2
            """,
            symbol, days,
        )
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df = df.set_index("date").sort_index()
    df.index = pd.to_datetime(df.index)
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype(int)
    return df


async def latest_bar_date(pool: asyncpg.Pool, symbol: str) -> date | None:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT MAX(date) FROM daily_bars WHERE symbol = $1", symbol
        )


async def upsert_bars(pool: asyncpg.Pool, symbol: str, df: pd.DataFrame) -> int:
    """Insert/update bars from a DataFrame. Returns row count touched."""
    if df.empty:
        return 0
    records = [
        (
            symbol,
            ts.date() if hasattr(ts, "date") else ts,
            float(row["open"]),
            float(row["high"]),
            float(row["low"]),
            float(row["close"]),
            int(row["volume"]),
        )
        for ts, row in df.iterrows()
    ]
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(
                """
                INSERT INTO daily_bars (symbol, date, open, high, low, close, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (symbol, date) DO UPDATE
                  SET open = EXCLUDED.open,
                      high = EXCLUDED.high,
                      low  = EXCLUDED.low,
                      close = EXCLUDED.close,
                      volume = EXCLUDED.volume
                """,
                records,
            )
    return len(records)
