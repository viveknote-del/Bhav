"""Alpha Vantage implementation of MarketDataProvider.

Use this when yfinance is being rate-limited or blocked from your IP.

Free-tier reality (as of 2026):
- 25 API calls / day
- 5 calls / minute
- One NIFTY 50 scan needs 50 calls — so a free key can't do daily scans.

Symbol format mapping:
  yfinance       Alpha Vantage
  RELIANCE.NS  → RELIANCE.BSE   (dual-listed; AV's NSE coverage is spotty)
  TATA.BO      → TATA.BSE

The `daily_bars` cache in this app means a freshly seeded universe + a few
scans can warm a meaningful window before the quota bites. For real daily
operation, either upgrade to Alpha Vantage Premium ($50/mo) or swap to
Twelve Data (800 req/day free) using this file as a template.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Any

import httpx
import pandas as pd

from config import settings
from providers.market_data import InstrumentInfo, MarketDataProvider, Quote

logger = logging.getLogger(__name__)

ALPHAVANTAGE_BASE = "https://www.alphavantage.co/query"
HTTP_TIMEOUT = 15.0
MAX_CONCURRENT = 3                # well below the 5/min limit


def _av_symbol(yf_symbol: str) -> str:
    """Translate a yfinance-style ticker to the Alpha Vantage form."""
    if yf_symbol.endswith(".NS") or yf_symbol.endswith(".BO"):
        return yf_symbol.rsplit(".", 1)[0] + ".BSE"
    return yf_symbol


def _parse_daily(payload: dict) -> pd.DataFrame:
    """Convert Alpha Vantage's TIME_SERIES_DAILY response into our standard
    OHLCV DataFrame. Returns empty on errors / quota notes."""
    if "Error Message" in payload:
        logger.warning("alphavantage.bad_symbol", extra={"reason": payload["Error Message"]})
        return pd.DataFrame()
    if "Note" in payload or "Information" in payload:
        logger.warning(
            "alphavantage.quota_or_throttle",
            extra={"reason": payload.get("Note") or payload.get("Information")},
        )
        return pd.DataFrame()

    series = payload.get("Time Series (Daily)")
    if not series:
        return pd.DataFrame()

    rows = []
    for d_str, ohlcv in series.items():
        rows.append({
            "date":   pd.Timestamp(d_str),
            "open":   float(ohlcv["1. open"]),
            "high":   float(ohlcv["2. high"]),
            "low":    float(ohlcv["3. low"]),
            "close":  float(ohlcv["4. close"]),
            "volume": int(ohlcv["5. volume"]),
        })
    df = pd.DataFrame(rows).set_index("date").sort_index()
    df.index = df.index.normalize()
    return df


class AlphaVantageProvider(MarketDataProvider):
    def __init__(self) -> None:
        if not settings.alphavantage_api_key:
            raise RuntimeError(
                "ALPHAVANTAGE_API_KEY is not set. Get a free key at "
                "https://www.alphavantage.co/support/#api-key and add it to .env."
            )
        self._sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def _fetch_daily(self, av_symbol: str, full: bool) -> dict:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": av_symbol,
            "outputsize": "full" if full else "compact",
            "apikey": settings.alphavantage_api_key,
        }
        async with self._sem:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                r = await client.get(ALPHAVANTAGE_BASE, params=params)
                r.raise_for_status()
                return r.json()

    async def get_bars(self, symbol: str, days: int) -> pd.DataFrame:
        av_symbol = _av_symbol(symbol)
        # "compact" returns 100 most-recent bars — enough for ≤90-day windows
        # and one call lighter on the meter. "full" needed for the 252-day
        # 52-week lookback.
        full = days > 100
        try:
            payload = await self._fetch_daily(av_symbol, full=full)
        except Exception as e:                                # noqa: BLE001
            logger.warning("alphavantage.fetch_failed", extra={"symbol": symbol, "error": str(e)})
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = _parse_daily(payload)
        if df.empty:
            return df
        return df.tail(days)

    async def get_quote(self, symbol: str) -> Quote | None:
        bars = await self.get_bars(symbol, days=1)
        if bars.empty:
            return None
        row = bars.iloc[-1]
        as_of = bars.index[-1]
        return Quote(
            symbol=symbol,
            price=float(row["close"]),
            volume=int(row["volume"]),
            as_of=as_of.date() if isinstance(as_of, (datetime, pd.Timestamp)) else date.today(),
        )

    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        # Alpha Vantage's OVERVIEW endpoint is US-only on the free tier and
        # spotty for Indian markets. We rely on the bundled NIFTY_50 seed
        # for name/sector instead; market_cap stays null until upgraded.
        return None
