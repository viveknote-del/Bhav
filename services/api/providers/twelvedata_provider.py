"""Twelve Data implementation of MarketDataProvider.

Free-tier reality (as of 2026):
- 800 API credits / day  (vs Alpha Vantage's 25 — that's why this exists)
- 8 calls / minute
- One NIFTY 50 scan = 50 calls, so a free key sustains ~16 scans/day.
  Plenty for one EOD scan + an intraday loop every 30 min.

Symbol format mapping:
  yfinance       Twelve Data
  RELIANCE.NS  → symbol=RELIANCE, exchange=NSE
  TATAMOTORS.BO → symbol=TATAMOTORS, exchange=BSE

Endpoint:
  GET https://api.twelvedata.com/time_series
      ?symbol=...&exchange=...&interval=1day&outputsize=N&apikey=...
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime

import httpx
import pandas as pd

from config import settings
from providers.market_data import InstrumentInfo, MarketDataProvider, Quote

logger = logging.getLogger(__name__)

TWELVEDATA_BASE = "https://api.twelvedata.com/time_series"
HTTP_TIMEOUT = 15.0
MAX_CONCURRENT = 4                # well under the 8/min limit


def _split_symbol(yf_symbol: str) -> tuple[str, str | None]:
    """Translate a yfinance ticker to Twelve Data's (symbol, exchange) pair."""
    if yf_symbol.endswith(".NS"):
        return yf_symbol[:-3], "NSE"
    if yf_symbol.endswith(".BO"):
        return yf_symbol[:-3], "BSE"
    return yf_symbol, None


def _parse_values(payload: dict) -> pd.DataFrame:
    """Convert a Twelve Data time_series payload into our OHLCV DataFrame."""
    status = payload.get("status")
    if status == "error":
        logger.warning(
            "twelvedata.error",
            extra={"code": payload.get("code"), "reason": payload.get("message", "")[:200]},
        )
        return pd.DataFrame()

    values = payload.get("values")
    if not values:
        return pd.DataFrame()

    rows = []
    for v in values:
        rows.append({
            "date":   pd.Timestamp(v["datetime"]),
            "open":   float(v["open"]),
            "high":   float(v["high"]),
            "low":    float(v["low"]),
            "close":  float(v["close"]),
            "volume": int(float(v["volume"])) if v.get("volume") else 0,
        })
    df = pd.DataFrame(rows).set_index("date").sort_index()
    df.index = df.index.normalize()
    return df


class TwelveDataProvider(MarketDataProvider):
    def __init__(self) -> None:
        if not settings.twelvedata_api_key:
            raise RuntimeError(
                "TWELVEDATA_API_KEY is not set. Get a free key at "
                "https://twelvedata.com/register and add it to .env."
            )
        self._sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def _fetch(self, symbol: str, exchange: str | None, outputsize: int) -> dict:
        params: dict[str, str] = {
            "symbol": symbol,
            "interval": "1day",
            "outputsize": str(min(outputsize, 5000)),
            "apikey": settings.twelvedata_api_key,
        }
        if exchange:
            params["exchange"] = exchange
        async with self._sem:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                r = await client.get(TWELVEDATA_BASE, params=params)
                r.raise_for_status()
                return r.json()

    async def get_bars(self, symbol: str, days: int) -> pd.DataFrame:
        sym, exchange = _split_symbol(symbol)
        try:
            # Pad outputsize: weekends/holidays waste calendar days, so ask
            # for ~1.5× the trading-day window plus a small floor.
            payload = await self._fetch(sym, exchange, outputsize=int(days * 1.5) + 10)
        except Exception as e:                                # noqa: BLE001
            logger.warning(
                "twelvedata.fetch_failed",
                extra={"symbol": symbol, "reason": str(e)[:200]},
            )
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = _parse_values(payload)
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
        # Twelve Data has a /quote endpoint that returns name/exchange but
        # not sector/industry on the free tier. Rely on the bundled NIFTY_50
        # seed for that metadata instead.
        return None
