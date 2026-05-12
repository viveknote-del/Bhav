from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WatchlistItemOut(BaseModel):
    symbol: str
    name: str
    sector: str | None = None
    exchange: Literal["NSE", "BSE"]
    notes: str | None = None
    added_at: datetime


class WatchlistAddIn(BaseModel):
    symbol: str = Field(min_length=2, max_length=32)
    notes: str | None = Field(default=None, max_length=500)
