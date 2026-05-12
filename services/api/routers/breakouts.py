from __future__ import annotations

from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from db import get_pool
from models.scan import BreakoutListOut, BreakoutOut
from repositories import breakout_repo
from services import scan_service

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
