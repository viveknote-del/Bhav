"""yfinance implementation of MarketDataProvider.

NSE tickers use '.NS' suffix, BSE uses '.BO'. yfinance handles both natively.
All calls run in a thread executor so we don't block the event loop —
yfinance is synchronous.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf

from providers.market_data import InstrumentInfo, MarketDataProvider, Quote

logger = logging.getLogger(__name__)


class YFinanceProvider(MarketDataProvider):
    async def get_bars(self, symbol: str, days: int) -> pd.DataFrame:
        def _fetch() -> pd.DataFrame:
            end = datetime.now()
            start = end - timedelta(days=int(days * 1.6) + 10)  # extra slack for weekends/holidays
            df = yf.Ticker(symbol).history(start=start, end=end, auto_adjust=False)
            if df.empty:
                return df
            df = df.rename(columns={
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume",
            })[["open", "high", "low", "close", "volume"]]
            df.index = df.index.tz_localize(None).normalize()
            return df.tail(days)

        try:
            return await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.warning("yfinance.get_bars failed", extra={"symbol": symbol, "error": str(e)})
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

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
                info = yf.Ticker(symbol).info or {}
            except Exception as e:
                logger.warning("yfinance.get_info failed", extra={"symbol": symbol, "error": str(e)})
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
