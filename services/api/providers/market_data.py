"""
Market data provider interface.

HARD RULE: Never call yfinance / broker SDKs directly from services, workers,
or routers. All market data flows through this interface so we can swap
providers without touching business logic.

See providers/yfinance_provider.py for the only v1 implementation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class InstrumentInfo:
    """Static-ish metadata for a tradable instrument."""
    symbol: str           # e.g. 'RELIANCE.NS'
    exchange: str         # 'NSE' or 'BSE'
    name: str
    sector: str | None
    industry: str | None
    market_cap: float | None


@dataclass(frozen=True)
class Quote:
    """Most recent price snapshot."""
    symbol: str
    price: float
    volume: int
    as_of: date


class MarketDataProvider(ABC):
    """Abstract base for market data providers (yfinance, brokers, etc.)."""

    @abstractmethod
    async def get_bars(self, symbol: str, days: int) -> pd.DataFrame:
        """
        Return last `days` of daily OHLCV bars.

        DataFrame is indexed by date (DatetimeIndex) with columns:
        open, high, low, close, volume. Empty DataFrame if no data.
        """
        ...

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote | None:
        """Return latest quote, or None if symbol can't be priced right now."""
        ...

    @abstractmethod
    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        """Return static metadata (name, sector, market cap) for a symbol."""
        ...
