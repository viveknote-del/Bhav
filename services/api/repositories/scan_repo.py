"""Raw asyncpg queries for scan_runs."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

import asyncpg


async def create_scan(
    pool: asyncpg.Pool, scan_type: str, universe_size: int
) -> UUID:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO scan_runs (scan_type, universe_size, status)
            VALUES ($1, $2, 'RUNNING')
            RETURNING id
            """,
            scan_type, universe_size,
        )


async def complete_scan(
    pool: asyncpg.Pool, scan_id: UUID, breakouts_found: int, finished_at: datetime
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE scan_runs
               SET status = 'COMPLETED',
                   breakouts_found = $2,
                   finished_at = $3
             WHERE id = $1
            """,
            scan_id, breakouts_found, finished_at,
        )


async def fail_scan(pool: asyncpg.Pool, scan_id: UUID, error: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE scan_runs
               SET status = 'FAILED',
                   error = $2,
                   finished_at = now()
             WHERE id = $1
            """,
            scan_id, error[:2000],
        )


async def get_scan(pool: asyncpg.Pool, scan_id: UUID) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT id, started_at, finished_at, scan_type, universe_size,
                   breakouts_found, status, error, summary
              FROM scan_runs
             WHERE id = $1
            """,
            scan_id,
        )


async def update_summary(pool: asyncpg.Pool, scan_id: UUID, summary: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE scan_runs SET summary = $2 WHERE id = $1",
            scan_id, summary,
        )


async def list_scans(
    pool: asyncpg.Pool, limit: int = 20, offset: int = 0
) -> tuple[list[asyncpg.Record], int]:
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM scan_runs")
        rows = await conn.fetch(
            """
            SELECT id, started_at, finished_at, scan_type, universe_size,
                   breakouts_found, status, error, summary
              FROM scan_runs
             ORDER BY started_at DESC
             LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
        return list(rows), int(total or 0)
