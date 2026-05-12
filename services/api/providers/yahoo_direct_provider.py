"""Direct Yahoo Finance chart-API provider.

Bypasses the yfinance library entirely and hits the public chart endpoint:

    GET https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}
        ?range=...&interval=1d

This is the URL Yahoo's website itself uses — same one verified working
from the user's mobile carrier (the JSON-with-RELIANCE.NS screenshot).
It avoids the cookie/crumb dance that yfinance does on every fresh
session, which is what Yahoo's edge throttles most aggressively in 2025+.

No API key. No quota. Free. Covers anything Yahoo's website covers
(full NSE + BSE for Indian equities). If your IP gets blocked, the
abstraction lets you swap to a different provider — same as before.

Uses curl_cffi for browser impersonation when available (already a
project dep) and falls back to httpx if curl_cffi isn't installed.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Any

import pandas as pd

from providers.market_data import InstrumentInfo, MarketDataProvider, Quote

logger = logging.getLogger(__name__)

CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
HTTP_TIMEOUT = 12.0
MAX_CONCURRENT = 5


def _range_for_days(days: int) -> str:
    """Smallest Yahoo `range` that comfortably covers `days` trading days.

    Yahoo's range values quantize to: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y,
    10y, ytd, max. We pad ~1.5× because the range counts calendar days,
    not trading days.
    """
    if days <= 5:    return "5d"
    if days <= 22:   return "1mo"
    if days <= 65:   return "3mo"
    if days <= 130:  return "6mo"
    if days <= 260:  return "1y"
    if days <= 520:  return "2y"
    if days <= 1300: return "5y"
    return "max"


# ──────────────────── session ──────────────────────

_session: Any | None = None
_session_kind: str = "uninitialized"


def _get_session() -> tuple[Any, str]:
    """Return (session, kind). Kind is 'curl_cffi' or 'httpx'."""
    global _session, _session_kind
    if _session is not None:
        return _session, _session_kind

    try:
        from curl_cffi import requests as crequests          # type: ignore
        _session = crequests.Session(impersonate="chrome")
        _session_kind = "curl_cffi"
        logger.info("yahoo_direct.session", extra={"kind": "curl_cffi"})
    except Exception:                                         # noqa: BLE001
        import httpx
        _session = httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        })
        _session_kind = "httpx"
        logger.info("yahoo_direct.session", extra={"kind": "httpx"})
    return _session, _session_kind


# ──────────────────── parsing ──────────────────────

def _parse_chart(payload: dict) -> pd.DataFrame:
    """Convert a /v8/finance/chart response into our OHLCV DataFrame."""
    chart = payload.get("chart") or {}
    err = chart.get("error")
    if err:
        logger.warning(
            "yahoo_direct.api_error",
            extra={"code": err.get("code"), "reason": err.get("description", "")[:200]},
        )
        return pd.DataFrame()

    result = (chart.get("result") or [None])[0]
    if not result:
        return pd.DataFrame()

    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quote_list = indicators.get("quote") or [{}]
    quote = quote_list[0] if quote_list else {}

    opens, highs, lows, closes, volumes = (
        quote.get("open") or [],
        quote.get("high") or [],
        quote.get("low") or [],
        quote.get("close") or [],
        quote.get("volume") or [],
    )
    if not timestamps:
        return pd.DataFrame()

    rows = []
    for ts, o, h, lo, c, v in zip(timestamps, opens, highs, lows, closes, volumes):
        # Skip rows where any OHLC is null (Yahoo emits these for non-trading days
        # that fall inside the range window)
        if None in (o, h, lo, c):
            continue
        rows.append({
            "date":   pd.Timestamp(ts, unit="s", tz="UTC").tz_convert(None),
            "open":   float(o),
            "high":   float(h),
            "low":    float(lo),
            "close":  float(c),
            "volume": int(v) if v is not None else 0,
        })

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).set_index("date").sort_index()
    df.index = df.index.normalize()
    return df


# ──────────────────── provider ──────────────────────

class YahooDirectProvider(MarketDataProvider):
    def __init__(self) -> None:
        self._sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def _fetch(self, symbol: str, days: int) -> dict:
        url = f"{CHART_BASE}/{symbol}"
        params = {"range": _range_for_days(days), "interval": "1d"}
        session, kind = _get_session()

        if kind == "curl_cffi":
            # curl_cffi is synchronous → run in thread
            def _go() -> dict:
                r = session.get(url, params=params, timeout=HTTP_TIMEOUT)
                r.raise_for_status()
                return r.json()
            return await asyncio.to_thread(_go)
        else:
            r = await session.get(url, params=params)
            r.raise_for_status()
            return r.json()

    async def get_bars(self, symbol: str, days: int) -> pd.DataFrame:
        async with self._sem:
            try:
                payload = await self._fetch(symbol, days)
            except Exception as e:                            # noqa: BLE001
                logger.warning(
                    "yahoo_direct.fetch_failed",
                    extra={"symbol": symbol, "reason": str(e)[:200]},
                )
                return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = _parse_chart(payload)
        return df.tail(days) if not df.empty else df

    async def get_bars_many(self, symbols: list[str], days: int) -> dict[str, pd.DataFrame]:
        """Concurrent per-symbol fetches with the same semaphore. The chart
        endpoint has no batch form, but it's lightweight enough that 5
        parallel calls are fine."""
        tasks = {sym: asyncio.create_task(self.get_bars(sym, days)) for sym in symbols}
        out: dict[str, pd.DataFrame] = {}
        for sym, task in tasks.items():
            df = await task
            if not df.empty:
                out[sym] = df
        return out

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
        # The chart endpoint's `meta` block has name/exchange but not
        # sector/industry/market_cap. The bundled NIFTY_50 seed covers
        # name+sector; market_cap stays null. Calling /v7/finance/quote
        # for market_cap requires the crumb dance — defeats the point.
        return None
