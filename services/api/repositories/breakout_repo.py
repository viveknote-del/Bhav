"""Raw asyncpg queries for breakouts."""
from __future__ import annotations

import json
from typing import Iterable
from uuid import UUID

import asyncpg

from services.breakout.types import BreakoutSignal


async def insert_breakouts(
    pool: asyncpg.Pool,
    scan_run_id: UUID,
    scored: Iterable[tuple[BreakoutSignal, float]],
) -> int:
    """Insert all detected breakouts in one transaction. Returns count."""
    records = []
    for signal, score in scored:
        records.append((
            scan_run_id,
            signal.symbol,
            signal.breakout_type,
            signal.pattern_subtype,
            float(signal.price),
            float(signal.breakout_level) if signal.breakout_level is not None else None,
            float(signal.volume_ratio),
            float(score),
            json.dumps(signal.indicators) if signal.indicators else None,
        ))
    if not records:
        return 0

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(
                """
                INSERT INTO breakouts (
                    scan_run_id, symbol, breakout_type, pattern_subtype,
                    price, breakout_level, volume_ratio, composite_score, indicators
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                """,
                records,
            )
    return len(records)


async def list_breakouts(
    pool: asyncpg.Pool,
    scan_run_id: UUID | None = None,
    breakout_type: str | None = None,
    min_score: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[asyncpg.Record], int]:
    where: list[str] = []
    params: list = []
    if scan_run_id is not None:
        params.append(scan_run_id)
        where.append(f"scan_run_id = ${len(params)}")
    if breakout_type:
        params.append(breakout_type)
        where.append(f"breakout_type = ${len(params)}")
    if min_score is not None:
        params.append(min_score)
        where.append(f"composite_score >= ${len(params)}")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM breakouts {where_sql}", *params
        )
        params_with_paging = params + [limit, offset]
        rows = await conn.fetch(
            f"""
            SELECT id, scan_run_id, symbol, detected_at, breakout_type,
                   pattern_subtype, price, breakout_level, volume_ratio,
                   composite_score, indicators, ai_commentary, news_links
              FROM breakouts
              {where_sql}
             ORDER BY composite_score DESC
             LIMIT ${len(params_with_paging) - 1} OFFSET ${len(params_with_paging)}
            """,
            *params_with_paging,
        )
        return list(rows), int(total or 0)


async def get_breakout(pool: asyncpg.Pool, breakout_id: UUID) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT id, scan_run_id, symbol, detected_at, breakout_type,
                   pattern_subtype, price, breakout_level, volume_ratio,
                   composite_score, indicators, ai_commentary, news_links
              FROM breakouts
             WHERE id = $1
            """,
            breakout_id,
        )
