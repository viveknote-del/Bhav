"""Single place to construct the active MarketDataProvider.

Reads `settings.market_data_provider` and returns the matching impl.
Add new providers here; never instantiate them directly elsewhere.
"""
from __future__ import annotations

from functools import cache

from config import settings
from providers.alphavantage_provider import AlphaVantageProvider
from providers.market_data import MarketDataProvider
from providers.yfinance_provider import YFinanceProvider

_SUPPORTED = ("yfinance", "alphavantage")


@cache
def get_market_data_provider() -> MarketDataProvider:
    name = settings.market_data_provider.lower()
    if name == "yfinance":
        return YFinanceProvider()
    if name in ("alphavantage", "alpha_vantage", "av"):
        return AlphaVantageProvider()
    raise RuntimeError(
        f"Unknown MARKET_DATA_PROVIDER: {settings.market_data_provider!r}. "
        f"Supported: {', '.join(_SUPPORTED)}."
    )
