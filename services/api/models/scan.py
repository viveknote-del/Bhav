from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ScanType = Literal["EOD", "INTRADAY"]
ScanStatus = Literal["RUNNING", "COMPLETED", "FAILED"]
BreakoutType = Literal["FIFTY_TWO_WEEK_HIGH", "CONSOLIDATION", "VOLUME_SPIKE", "PATTERN"]
PatternSubtype = Literal["FLAG", "CUP_HANDLE", "TRIANGLE"]


class ScanCreate(BaseModel):
    scan_type: ScanType = "EOD"


class ScanRunOut(BaseModel):
    id: UUID
    started_at: datetime
    finished_at: datetime | None
    scan_type: ScanType
    universe_size: int | None
    breakouts_found: int | None
    status: ScanStatus
    error: str | None
    summary: str | None


class ScanRunListOut(BaseModel):
    items: list[ScanRunOut]
    total: int
    page: int
    limit: int


class BreakoutOut(BaseModel):
    id: UUID
    scan_run_id: UUID
    symbol: str
    detected_at: datetime
    breakout_type: BreakoutType
    pattern_subtype: PatternSubtype | None
    price: float
    breakout_level: float | None
    volume_ratio: float | None
    composite_score: float
    indicators: dict | None
    ai_commentary: str | None
    news_links: list | None


class BreakoutListOut(BaseModel):
    items: list[BreakoutOut]
    total: int
    page: int
    limit: int


class ScanDetailOut(BaseModel):
    scan: ScanRunOut
    breakouts: list[BreakoutOut]
