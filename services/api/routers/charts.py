from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from db import get_pool
from models.instrument import ChartOut
from providers.factory import get_market_data_provider
from services import instrument_service

router = APIRouter(prefix="/v1/charts", tags=["charts"])


@router.get("/{symbol}", response_model=ChartOut)
async def get_chart(
    symbol: str,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    days: int = Query(default=180, ge=5, le=2000),
):
    provider = get_market_data_provider()
    chart = await instrument_service.get_chart(pool, provider, symbol, days)
    if chart is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown symbol: {symbol}")
    return chart
