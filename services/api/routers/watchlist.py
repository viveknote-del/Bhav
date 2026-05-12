from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from db import get_pool
from models.watchlist import WatchlistAddIn, WatchlistItemOut
from repositories import instrument_repo, watchlist_repo

router = APIRouter(prefix="/v1/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemOut])
async def list_watchlist(pool: Annotated[asyncpg.Pool, Depends(get_pool)]):
    rows = await watchlist_repo.list_watchlist(pool)
    return [
        WatchlistItemOut(
            symbol=r["symbol"],
            name=r["name"],
            sector=r["sector"],
            exchange=r["exchange"],
            notes=r["notes"],
            added_at=r["added_at"],
        )
        for r in rows
    ]


@router.post("", response_model=WatchlistItemOut, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    body: WatchlistAddIn,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
):
    inst = await instrument_repo.get_instrument(pool, body.symbol)
    if inst is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown symbol: {body.symbol}")

    await watchlist_repo.add_to_watchlist(pool, body.symbol, body.notes)
    rows = await watchlist_repo.list_watchlist(pool)
    item = next(r for r in rows if r["symbol"] == body.symbol)
    return WatchlistItemOut(
        symbol=item["symbol"],
        name=item["name"],
        sector=item["sector"],
        exchange=item["exchange"],
        notes=item["notes"],
        added_at=item["added_at"],
    )


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    symbol: str,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
):
    removed = await watchlist_repo.remove_from_watchlist(pool, symbol)
    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{symbol} not in watchlist")
    return None
