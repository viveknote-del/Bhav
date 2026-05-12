from __future__ import annotations

from typing import Annotated
from uuid import UUID

import asyncpg
from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Query, status

from arq_client import get_arq
from db import get_pool
from models.scan import ScanCreate, ScanDetailOut, ScanRunListOut, ScanRunOut
from repositories import scan_repo
from services import scan_service

router = APIRouter(prefix="/v1/scans", tags=["scans"])


@router.post("", response_model=ScanRunOut, status_code=status.HTTP_202_ACCEPTED)
async def trigger_scan(
    body: ScanCreate,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    arq: Annotated[ArqRedis, Depends(get_arq)],
):
    """Enqueue a scan job. Returns the scan_run row immediately;
    the worker fills in breakouts asynchronously. Poll GET /v1/scans/{id}
    to see when status flips to COMPLETED.
    """
    symbols = await pool.fetchval("SELECT COUNT(*) FROM instruments WHERE is_active")
    universe_size = int(symbols or 0)
    if universe_size == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Empty universe. Seed instruments first: `make seed`.",
        )

    scan_id = await scan_repo.create_scan(pool, body.scan_type, universe_size)
    await arq.enqueue_job("scan_eod", str(scan_id))

    row = await scan_repo.get_scan(pool, scan_id)
    return scan_service._scan_record_to_model(row)  # noqa: SLF001 — internal use


@router.get("", response_model=ScanRunListOut)
async def list_scans(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
):
    return await scan_service.list_scans(pool, page, limit)


@router.get("/{scan_id}", response_model=ScanDetailOut)
async def get_scan(
    scan_id: UUID,
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
):
    detail = await scan_service.get_scan_detail(pool, scan_id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    return detail
