from __future__ import annotations

from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from db import get_pool
from models.scan import BreakoutListOut, BreakoutOut
from repositories import breakout_repo
from services import commentary_service, scan_service

router = APIRouter(prefix="/v1/breakouts", tags=["breakouts"])


@router.get("", response_model=BreakoutListOut)
async def list_breakouts(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    scan_run_id: UUID | None = None,
    breakout_type: str | None = None,
    min_score: float | None = Query(default=None, ge=0, le=100),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    rows, total = await breakout_repo.list_breakouts(
        pool,
        scan_run_id=scan_run_id,
        breakout_type=breakout_type,
        min_score=min_score,
        limit=limit,
        offset=(page - 1) * limit,
    )
    return BreakoutListOut(
        items=[scan_service._breakout_record_to_model(r) for r in rows],  # noqa: SLF001
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{breakout_id}", response_model=BreakoutOut)
async def get_breakout(
    breakout_id: UUID,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
):
    row = await breakout_repo.get_breakout(pool, breakout_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Breakout not found")
    return scan_service._breakout_record_to_model(row)  # noqa: SLF001


@router.post("/{breakout_id}/commentary", response_model=BreakoutOut)
async def regenerate_commentary(
    breakout_id: UUID,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    force_news_refresh: bool = Query(default=False),
):
    """Synchronously (re)generate Claude commentary for a single breakout.

    Costs one Claude call and (optionally) one NewsAPI call. Use this
    when you want to retry a failed commentary or refresh after the
    prompt registry version bumped.
    """
    try:
        await commentary_service.generate_for_breakout(
            pool, breakout_id, force_news_refresh=force_news_refresh
        )
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Breakout not found")
    except RuntimeError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))

    row = await breakout_repo.get_breakout(pool, breakout_id)
    return scan_service._breakout_record_to_model(row)  # noqa: SLF001
