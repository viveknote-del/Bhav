"""Raw asyncpg queries for the `instruments` table. Returns dict rows;
services own conversion to Pydantic models.
"""
from __future__ import annotations

import asyncpg


async def list_instruments(
    pool: asyncpg.Pool,
    exchange: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[asyncpg.Record], int]:
    where = ["is_active"]
    params: list = []
    if exchange:
        params.append(exchange)
        where.append(f"exchange = ${len(params)}")
    if search:
        params.append(f"%{search.lower()}%")
        where.append(f"(LOWER(symbol) LIKE ${len(params)} OR LOWER(name) LIKE ${len(params)})")

    where_sql = " AND ".join(where)

    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM instruments WHERE {where_sql}", *params)
        params_with_paging = params + [limit, offset]
        rows = await conn.fetch(
            f"""
            SELECT symbol, exchange, name, sector, industry, market_cap, is_active, updated_at
              FROM instruments
             WHERE {where_sql}
             ORDER BY market_cap DESC NULLS LAST, symbol
             LIMIT ${len(params_with_paging) - 1} OFFSET ${len(params_with_paging)}
            """,
            *params_with_paging,
        )
        return list(rows), int(total or 0)


async def get_instrument(pool: asyncpg.Pool, symbol: str) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT symbol, exchange, name, sector, industry, market_cap, is_active, updated_at
              FROM instruments
             WHERE symbol = $1
            """,
            symbol,
        )


async def upsert_instrument(
    pool: asyncpg.Pool,
    symbol: str,
    exchange: str,
    name: str,
    sector: str | None,
    industry: str | None,
    market_cap: float | None,
) -> str:
    """Returns 'inserted' or 'updated' so the seeder can report counts."""
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """
            INSERT INTO instruments (symbol, exchange, name, sector, industry, market_cap, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, now())
            ON CONFLICT (symbol) DO UPDATE
              SET exchange   = EXCLUDED.exchange,
                  name       = EXCLUDED.name,
                  sector     = COALESCE(EXCLUDED.sector, instruments.sector),
                  industry   = COALESCE(EXCLUDED.industry, instruments.industry),
                  market_cap = COALESCE(EXCLUDED.market_cap, instruments.market_cap),
                  is_active  = true,
                  updated_at = now()
            RETURNING (xmax = 0) AS inserted
            """,
            symbol, exchange, name, sector, industry, market_cap,
        )
        return "inserted" if result and result["inserted"] else "updated"
