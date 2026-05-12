"""yfinance implementation of MarketDataProvider.

NSE tickers use '.NS', BSE uses '.BO'. yfinance handles both natively.
Synchronous calls run in `asyncio.to_thread` so we don't block the loop.

Hardening against Yahoo's aggressive rate-limiting (2025 onwards):
- A module-level `curl_cffi` Session impersonating Chrome is reused across
  calls. yfinance's `Ticker(..., session=...)` and `download(session=...)`
  signatures pick this up.
- Single-symbol fetches retry with exponential backoff (1s → 2s → 4s).
- For multi-symbol fetches the engine calls `get_bars_many`, which hits
  `yf.download` in batches — one HTTP request per batch instead of one
  per symbol. This is the biggest rate-limit win.

If your machine still gets empty bars after this, your IP is likely
blacklisted — switch networks (residential IP usually works) or swap
to a different provider behind the MarketDataProvider interface.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from providers.market_data import InstrumentInfo, MarketDataProvider, Quote

logger = logging.getLogger(__name__)

BATCH_SIZE = 20                           # symbols per yf.download call
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0


# ──────────────────── session ──────────────────────

_session: Any | None = None


def _get_session() -> Any | None:
    """Return a cached curl_cffi Session impersonating Chrome, or None if
    curl_cffi is not installed (yfinance still works without it)."""
    global _session
    if _session is not None:
        return _session
    try:
        from curl_cffi import requests as crequests          # type: ignore
        _session = crequests.Session(impersonate="chrome")
        logger.info("yfinance.session_initialized", extra={"impersonate": "chrome"})
    except Exception as e:                                    # noqa: BLE001
        logger.warning("yfinance.curl_cffi_unavailable", extra={"error": str(e)})
        _session = None
    return _session


# ──────────────────── helpers ──────────────────────

def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a yfinance DataFrame to (open, high, low, close, volume), tz-naive."""
    if df.empty:
        return df
    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume",
    })
    cols = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    df = df[cols]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index = df.index.normalize()
    return df.dropna()


def _date_window(days: int) -> tuple[datetime, datetime]:
    end = datetime.now()
    start = end - timedelta(days=int(days * 1.6) + 10)        # slack for weekends/holidays
    return start, end


# ──────────────────── provider ──────────────────────

class YFinanceProvider(MarketDataProvider):

    async def get_bars(self, symbol: str, days: int) -> pd.DataFrame:
        def _fetch_with_retry() -> pd.DataFrame:
            start, end = _date_window(days)
            last_exc: Exception | None = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    ticker = yf.Ticker(symbol, session=_get_session())
                    df = ticker.history(start=start, end=end, auto_adjust=False)
                    if not df.empty:
                        return _normalize(df).tail(days)
                except Exception as e:                        # noqa: BLE001
                    last_exc = e
                if attempt < MAX_RETRIES:
                    import time
                    time.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))
            if last_exc:
                logger.warning("yfinance.get_bars_failed", extra={"symbol": symbol, "error": str(last_exc)})
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        return await asyncio.to_thread(_fetch_with_retry)

    async def get_bars_many(self, symbols: list[str], days: int) -> dict[str, pd.DataFrame]:
        """Batch fetch — fewer HTTP round-trips, kinder on Yahoo's rate limiter.

        Returns a dict symbol → DataFrame. Symbols that fail are silently
        omitted; partial success is normal. Caller can iterate the dict
        and detect missing symbols.
        """
        def _fetch_batch(batch: list[str]) -> dict[str, pd.DataFrame]:
            start, end = _date_window(days)
            try:
                df = yf.download(
                    tickers=batch,
                    start=start,
                    end=end,
                    group_by="ticker",
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                    session=_get_session(),
                )
            except Exception as e:                            # noqa: BLE001
                logger.warning("yfinance.batch_failed", extra={"size": len(batch), "error": str(e)})
                return {}

            if df is None or df.empty:
                return {}

            out: dict[str, pd.DataFrame] = {}
            # yf.download returns a multi-level column index when len(batch) > 1,
            # and a flat column index when len(batch) == 1.
            if len(batch) == 1:
                norm = _normalize(df)
                if not norm.empty:
                    out[batch[0]] = norm.tail(days)
                return out

            for sym in batch:
                try:
                    sub = df[sym]
                except KeyError:
                    continue
                norm = _normalize(sub)
                if not norm.empty:
                    out[sym] = norm.tail(days)
            return out

        results: dict[str, pd.DataFrame] = {}
        for i in range(0, len(symbols), BATCH_SIZE):
            batch = symbols[i : i + BATCH_SIZE]
            batch_results = await asyncio.to_thread(_fetch_batch, batch)
            results.update(batch_results)
        return results

    async def get_quote(self, symbol: str) -> Quote | None:
        bars = await self.get_bars(symbol, days=1)
        if bars.empty:
            return None
        row = bars.iloc[-1]
        return Quote(
            symbol=symbol,
            price=float(row["close"]),
            volume=int(row["volume"]),
            as_of=bars.index[-1].date() if isinstance(bars.index[-1], (datetime, pd.Timestamp)) else date.today(),
        )

    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        def _fetch() -> InstrumentInfo | None:
            try:
                info = yf.Ticker(symbol, session=_get_session()).info or {}
            except Exception as e:                            # noqa: BLE001
                logger.warning("yfinance.get_info_failed", extra={"symbol": symbol, "error": str(e)})
                return None

            name = info.get("longName") or info.get("shortName")
            if not name:
                return None

            exchange = "NSE" if symbol.endswith(".NS") else "BSE" if symbol.endswith(".BO") else "UNKNOWN"
            return InstrumentInfo(
                symbol=symbol,
                exchange=exchange,
                name=name,
                sector=info.get("sector"),
                industry=info.get("industry"),
                market_cap=info.get("marketCap"),
            )

        return await asyncio.to_thread(_fetch)
