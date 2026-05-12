"""Single place to construct the active MarketDataProvider.

Reads `settings.market_data_provider` and returns the matching impl.
Add new providers here; never instantiate them directly elsewhere.
"""
from __future__ import annotations

from functools import cache

from config import settings
from providers.alphavantage_provider import AlphaVantageProvider
from providers.market_data import MarketDataProvider
from providers.twelvedata_provider import TwelveDataProvider
from providers.yahoo_direct_provider import YahooDirectProvider
from providers.yfinance_provider import YFinanceProvider

_SUPPORTED = ("yfinance", "yahoo_direct", "alphavantage", "twelvedata")


@cache
def get_market_data_provider() -> MarketDataProvider:
    name = settings.market_data_provider.lower().replace("_", "").replace("-", "")
    if name == "yfinance":
        return YFinanceProvider()
    if name in ("yahoodirect", "yahoo"):
        return YahooDirectProvider()
    if name in ("alphavantage", "av"):
        return AlphaVantageProvider()
    if name in ("twelvedata", "td"):
        return TwelveDataProvider()
    raise RuntimeError(
        f"Unknown MARKET_DATA_PROVIDER: {settings.market_data_provider!r}. "
        f"Supported: {', '.join(_SUPPORTED)}."
    )
