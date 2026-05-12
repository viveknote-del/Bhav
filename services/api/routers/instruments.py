from __future__ import annotations

from typing import Annotated, Literal

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from db import get_pool
from models.instrument import InstrumentListOut, InstrumentOut, RefreshResult
from providers.factory import get_market_data_provider
from services import instrument_service

router = APIRouter(prefix="/v1/instruments", tags=["instruments"])


@router.get("", response_model=InstrumentListOut)
async def list_instruments(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    exchange: Literal["NSE", "BSE"] | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=64),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    return await instrument_service.list_instruments(pool, exchange, search, page, limit)


@router.get("/{symbol}", response_model=InstrumentOut)
async def get_instrument(
    symbol: str,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
):
    from repositories.instrument_repo import get_instrument as _get

    row = await _get(pool, symbol)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown symbol: {symbol}")
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


@router.post("/refresh", response_model=RefreshResult)
async def refresh_universe(pool: Annotated[asyncpg.Pool, Depends(get_pool)]):
    """Re-fetch metadata for the NIFTY 50 universe from the market data provider."""
    provider = get_market_data_provider()
    return await instrument_service.refresh_universe(pool, provider)
