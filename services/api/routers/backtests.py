"""Backtest endpoint — replays detectors against cached daily_bars.

POST /v1/backtests runs synchronously. For NIFTY 50 over a 6-month
range this completes in <30s; if the universe grows or the range widens
we'd move this onto an arq worker.
"""
from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from db import get_pool
from models.backtest import BacktestIn, BacktestOut, DetectorSummary
from services.backtest import run_backtest

router = APIRouter(prefix="/v1/backtests", tags=["backtests"])


@router.post("", response_model=BacktestOut)
async def run_backtest_endpoint(
    body: BacktestIn,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
):
    if body.start > body.end:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "start must be on or before end")

    async with pool.acquire() as conn:
        symbols = [
            r["symbol"]
            for r in await conn.fetch(
                "SELECT symbol FROM instruments WHERE is_active ORDER BY symbol"
            )
        ]
    if not symbols:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No active instruments. Seed the universe first: `make seed`.",
        )

    summaries = await run_backtest(
        pool,
        symbols,
        start=body.start,
        end=body.end,
        forward_window_days=body.forward_window_days,
        win_threshold=body.win_threshold,
    )

    return BacktestOut(
        start=body.start,
        end=body.end,
        forward_window_days=body.forward_window_days,
        win_threshold=body.win_threshold,
        universe_size=len(symbols),
        summaries=[
            DetectorSummary(
                detector=s.detector,
                n_signals=s.n_signals,
                hit_rate=round(s.hit_rate, 4),
                win_rate=round(s.win_rate, 4),
                mean_forward_return=round(s.mean_forward_return, 4),
                mean_composite_score=round(s.mean_composite_score, 2),
            )
            for s in summaries
        ],
    )
