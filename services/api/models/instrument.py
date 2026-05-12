from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


Exchange = Literal["NSE", "BSE"]


class InstrumentOut(BaseModel):
    symbol: str
    exchange: Exchange
    name: str
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    is_active: bool = True
    updated_at: datetime


class InstrumentListOut(BaseModel):
    items: list[InstrumentOut]
    total: int
    page: int
    limit: int


class Bar(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChartOut(BaseModel):
    symbol: str
    bars: list[Bar]


class RefreshResult(BaseModel):
    inserted: int
    updated: int
    failed: list[str] = Field(default_factory=list)
