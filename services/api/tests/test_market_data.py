"""Unit tests for the market data provider interface.

Does NOT hit yfinance directly — those are integration tests and live
behind a network/online marker (not part of the default suite).
"""
from __future__ import annotations

import pytest

from providers.factory import get_market_data_provider
from providers.market_data import MarketDataProvider
from providers.yfinance_provider import YFinanceProvider


def test_factory_returns_yfinance_by_default():
    provider = get_market_data_provider()
    assert isinstance(provider, MarketDataProvider)
    assert isinstance(provider, YFinanceProvider)


def test_yfinance_provider_implements_interface():
    provider = YFinanceProvider()
    assert hasattr(provider, "get_bars")
    assert hasattr(provider, "get_quote")
    assert hasattr(provider, "get_instrument_info")


def test_factory_caches_provider_instance():
    p1 = get_market_data_provider()
    p2 = get_market_data_provider()
    assert p1 is p2


@pytest.mark.asyncio
async def test_yfinance_returns_empty_df_for_unknown_symbol():
    """Bad symbols should return an empty DataFrame rather than raising."""
    provider = YFinanceProvider()
    df = await provider.get_bars("DEFINITELY_NOT_A_REAL_TICKER_12345.NS", days=10)
    assert df.empty
