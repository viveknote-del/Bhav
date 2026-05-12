"""Integration test for scan_service against real Postgres.

Uses a mocked MarketDataProvider so we don't hit yfinance during tests —
synthetic bars give deterministic detector outcomes.
"""
from __future__ import annotations

import pandas as pd
import pytest
import pytest_asyncio
import asyncpg

from config import settings
from providers.market_data import MarketDataProvider, InstrumentInfo, Quote
from repositories import instrument_repo, scan_repo
from services import scan_service
from services.breakout import _swing_filter


@pytest.fixture(autouse=True)
def _bypass_swing_gate(monkeypatch):
    """Scan-orchestration tests focus on the pipeline (provider → detectors
    → scoring → persist), not on the swing-trade gate. The gate is unit-
    tested separately in test_swing_filter.py. Bypassing here lets us
    keep synthetic 252-bar fixtures simple without engineering trend +
    RSI + ADX into every one."""
    monkeypatch.setattr(
        _swing_filter,
        "evaluate",
        lambda bars: _swing_filter.SwingIndicators(0.0, 0.0, 0.0, 60.0, 30.0, True, None),
    )


def _flat_then_break(closes_top: float = 105.0) -> pd.DataFrame:
    """252 bars at 100.0 then today closes at 105.0 with volume 3x avg —
    triggers BOTH 52w-high AND volume-spike detectors."""
    closes = [100.0] * 252 + [closes_top]
    vols = [1_000_000] * 252 + [3_000_000]
    idx = pd.bdate_range(start="2025-01-01", periods=len(closes))
    return pd.DataFrame({
        "open":   [c * 0.99 for c in closes],
        "high":   [c * 1.01 for c in closes],
        "low":    [c * 0.98 for c in closes],
        "close":  closes,
        "volume": vols,
    }, index=idx)


def _quiet() -> pd.DataFrame:
    """Sideways bars — no detector should fire."""
    closes = [100.0] * 253
    vols = [1_000_000] * 253
    idx = pd.bdate_range(start="2025-01-01", periods=len(closes))
    return pd.DataFrame({
        "open":   closes,
        "high":   [c * 1.005 for c in closes],
        "low":    [c * 0.995 for c in closes],
        "close":  closes,
        "volume": vols,
    }, index=idx)


class FakeProvider(MarketDataProvider):
    def __init__(self, mapping: dict[str, pd.DataFrame]):
        self._mapping = mapping

    async def get_bars(self, symbol: str, days: int) -> pd.DataFrame:
        return self._mapping.get(symbol, pd.DataFrame()).tail(days)

    async def get_quote(self, symbol: str) -> Quote | None:
        return None

    async def get_instrument_info(self, symbol: str) -> InstrumentInfo | None:
        return None


@pytest_asyncio.fixture
async def pool():
    p = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    yield p
    await p.close()


TEST_SYMBOLS = ("_TEST_AAA.NS", "_TEST_BBB.NS", "_TEST_CCC.NS")


@pytest_asyncio.fixture
async def clean_db(pool):
    """Opt-in destructive fixture. The scan-orchestration integration
    tests need a clean DB to assert exact counts. Default pytest runs
    skip them so a shared dev DB never gets wiped accidentally.

    Even when enabled, this only touches our `_TEST_*.NS` test symbols —
    production data is preserved by symbol-scoped DELETEs.
    """
    import os
    if not os.environ.get("BHAV_DESTRUCTIVE_TESTS"):
        pytest.skip("destructive integration test — set BHAV_DESTRUCTIVE_TESTS=1 to run")

    async def _purge():
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM breakouts WHERE symbol = ANY($1::text[])", list(TEST_SYMBOLS)
            )
            await conn.execute(
                "DELETE FROM daily_bars WHERE symbol = ANY($1::text[])", list(TEST_SYMBOLS)
            )
            # scan_runs aren't symbol-scoped, but the orphans we'd leave
            # behind are tiny and don't break anything; leave them.
            await conn.execute(
                "DELETE FROM instruments WHERE symbol = ANY($1::text[])", list(TEST_SYMBOLS)
            )
    await _purge()
    yield
    await _purge()


@pytest_asyncio.fixture
async def fixture_universe(pool, clean_db):
    """Seed 3 symbols: 2 will break out, 1 won't."""
    for symbol, name in [
        ("_TEST_AAA.NS", "Breakout Co A"),
        ("_TEST_BBB.NS", "Breakout Co B"),
        ("_TEST_CCC.NS", "Quiet Co C"),
    ]:
        await instrument_repo.upsert_instrument(
            pool, symbol=symbol, exchange="NSE", name=name,
            sector="Test", industry=None, market_cap=None,
        )


@pytest.mark.asyncio
async def test_run_scan_persists_breakouts(pool, fixture_universe):
    provider = FakeProvider({
        "_TEST_AAA.NS": _flat_then_break(),
        "_TEST_BBB.NS": _flat_then_break(closes_top=108.0),
        "_TEST_CCC.NS": _quiet(),
    })
    scan_id = await scan_service.create_and_run_scan(pool, provider, scan_type="EOD")

    detail = await scan_service.get_scan_detail(pool, scan_id)
    assert detail is not None
    assert detail.scan.status == "COMPLETED"
    assert detail.scan.universe_size == 3

    by_symbol = {b.symbol for b in detail.breakouts}
    assert "_TEST_AAA.NS" in by_symbol
    assert "_TEST_BBB.NS" in by_symbol
    assert "_TEST_CCC.NS" not in by_symbol

    for b in detail.breakouts:
        assert 0.0 <= b.composite_score <= 100.0
        assert b.breakout_type in ("FIFTY_TWO_WEEK_HIGH", "VOLUME_SPIKE")


@pytest.mark.asyncio
async def test_scan_handles_provider_failure_for_one_symbol(pool, fixture_universe):
    class FlakyProvider(FakeProvider):
        async def get_bars(self, symbol: str, days: int) -> pd.DataFrame:
            if symbol == "_TEST_BBB.NS":
                raise RuntimeError("simulated rate-limit")
            return await super().get_bars(symbol, days)

    provider = FlakyProvider({
        "_TEST_AAA.NS": _flat_then_break(),
        "_TEST_CCC.NS": _quiet(),
    })
    scan_id = await scan_service.create_and_run_scan(pool, provider, scan_type="EOD")
    detail = await scan_service.get_scan_detail(pool, scan_id)
    assert detail.scan.status == "COMPLETED"          # one bad symbol shouldn't kill the scan
    symbols = {b.symbol for b in detail.breakouts}
    assert symbols == {"_TEST_AAA.NS"}                       # AAA detected, BBB errored, CCC quiet


@pytest.mark.asyncio
async def test_list_scans_returns_recent_first(pool, fixture_universe):
    provider = FakeProvider({s: _quiet() for s in ("_TEST_AAA.NS", "_TEST_BBB.NS", "_TEST_CCC.NS")})
    await scan_service.create_and_run_scan(pool, provider)
    await scan_service.create_and_run_scan(pool, provider)

    listing = await scan_service.list_scans(pool, page=1, limit=10)
    assert listing.total == 2
    # ordered DESC by started_at
    assert listing.items[0].started_at >= listing.items[1].started_at
