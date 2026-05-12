"""Raw asyncpg queries for the personal watchlist."""
from __future__ import annotations

import asyncpg


async def list_watchlist(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return list(await conn.fetch(
            """
            SELECT w.symbol, w.notes, w.added_at,
                   i.name, i.sector, i.exchange
              FROM watchlist w
              JOIN instruments i ON i.symbol = w.symbol
             ORDER BY w.added_at DESC
            """
        ))


async def add_to_watchlist(pool: asyncpg.Pool, symbol: str, notes: str | None) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO watchlist (symbol, notes)
            VALUES ($1, $2)
            ON CONFLICT (symbol) DO UPDATE SET notes = EXCLUDED.notes
            """,
            symbol, notes,
        )


async def remove_from_watchlist(pool: asyncpg.Pool, symbol: str) -> bool:
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM watchlist WHERE symbol = $1", symbol
        )
    return result.endswith(" 1")
