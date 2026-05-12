"""Integration tests for instrument_service against a live Postgres.

Requires `docker compose up -d` and migrations applied. Each test uses
a fresh transaction that is rolled back so tests don't pollute each other.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
import asyncpg

from config import settings
from services import instrument_service


@pytest_asyncio.fixture
async def pool():
    p = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=2)
    yield p
    await p.close()


@pytest_asyncio.fixture
async def clean_instruments(pool):
    """⚠ DESTRUCTIVE: TRUNCATEs the instruments table (and cascades).
    Run only against a dedicated test DB. Opt in via the env var below.
    Default pytest invocations skip the tests that use this fixture."""
    import os
    if not os.environ.get("BHAV_DESTRUCTIVE_TESTS"):
        pytest.skip("destructive integration test — set BHAV_DESTRUCTIVE_TESTS=1 to run")
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE instruments CASCADE")
    yield
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE instruments CASCADE")


@pytest.mark.asyncio
async def test_seed_offline_inserts_nifty_50(pool, clean_instruments):
    """Seeding an empty table should report 50 inserts, 0 updates."""
    result = await instrument_service.seed_universe_offline(pool)
    assert result.inserted == 50
    assert result.updated == 0
    assert result.failed == []


@pytest.mark.asyncio
async def test_seed_offline_is_idempotent(pool, clean_instruments):
    """Running the seeder twice should produce updates, not inserts."""
    first = await instrument_service.seed_universe_offline(pool)
    second = await instrument_service.seed_universe_offline(pool)
    assert first.inserted == 50
    assert second.inserted == 0
    assert second.updated == 50


@pytest.mark.asyncio
async def test_list_instruments_paginates(pool, clean_instruments):
    await instrument_service.seed_universe_offline(pool)

    page_1 = await instrument_service.list_instruments(pool, exchange=None, search=None, page=1, limit=20)
    assert page_1.total == 50
    assert len(page_1.items) == 20
    assert page_1.page == 1

    page_3 = await instrument_service.list_instruments(pool, exchange=None, search=None, page=3, limit=20)
    assert len(page_3.items) == 10


@pytest.mark.asyncio
async def test_list_instruments_search_matches_name_or_symbol(pool, clean_instruments):
    await instrument_service.seed_universe_offline(pool)

    by_symbol = await instrument_service.list_instruments(pool, exchange=None, search="RELIANCE", page=1, limit=50)
    assert by_symbol.total == 1
    assert by_symbol.items[0].symbol == "RELIANCE.NS"

    by_name = await instrument_service.list_instruments(pool, exchange=None, search="bank", page=1, limit=50)
    assert by_name.total >= 4  # HDFCBANK, ICICIBANK, KOTAKBANK, AXISBANK, INDUSINDBK, SBIN, etc.
