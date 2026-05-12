"""NewsAPI client with aggressive (symbol, date) caching.

Free tier = 100 requests / day. We cache per (symbol, scan_date) so the
same scan never refetches; reruns and manual regenerations hit the cache.

If NEWSAPI_KEY is not set, every call returns []. The system degrades
gracefully: commentary still generates without news context.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import asyncpg
import httpx

from config import settings

logger = logging.getLogger(__name__)

NEWSAPI_ENDPOINT = "https://newsapi.org/v2/everything"
LOOKBACK_DAYS = 3
MAX_HEADLINES = 5


@dataclass(frozen=True)
class Headline:
    title: str
    url: str
    source: str
    published_at: str  # ISO 8601

    def as_dict(self) -> dict:
        return {"title": self.title, "url": self.url, "source": self.source, "published_at": self.published_at}


def _query_for_symbol(symbol: str, name: str | None) -> str:
    """Compose a NewsAPI query. Symbol alone produces poor recall (most
    tickers aren't mentioned in headlines); we prefer the issuer name and
    fall back to the symbol stripped of its exchange suffix."""
    if name:
        return f'"{name}"'
    return symbol.replace(".NS", "").replace(".BO", "")


async def get_headlines(
    pool: asyncpg.Pool,
    symbol: str,
    name: str | None,
    scan_date: date,
    *,
    force_refresh: bool = False,
) -> list[Headline]:
    """Cache-first fetch. Returns [] silently on quota or network errors —
    commentary should still generate without news."""
    if not force_refresh:
        cached = await _read_cache(pool, symbol, scan_date)
        if cached is not None:
            return cached

    if not settings.newsapi_key:
        return []

    try:
        headlines = await _fetch_from_newsapi(symbol, name, scan_date)
    except Exception as e:                              # noqa: BLE001
        logger.warning("news.fetch_failed", extra={"symbol": symbol, "error": str(e)})
        return []

    await _write_cache(pool, symbol, scan_date, headlines)
    return headlines


async def _fetch_from_newsapi(symbol: str, name: str | None, scan_date: date) -> list[Headline]:
    from_date = (scan_date - timedelta(days=LOOKBACK_DAYS)).isoformat()
    params = {
        "q": _query_for_symbol(symbol, name),
        "from": from_date,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": MAX_HEADLINES,
        "apiKey": settings.newsapi_key,
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get(NEWSAPI_ENDPOINT, params=params)
        r.raise_for_status()
        payload = r.json()

    articles = payload.get("articles", [])[:MAX_HEADLINES]
    return [
        Headline(
            title=a.get("title", "").strip(),
            url=a.get("url", ""),
            source=(a.get("source") or {}).get("name", "") or "",
            published_at=a.get("publishedAt", ""),
        )
        for a in articles
        if a.get("title")
    ]


# ──────────────────── cache helpers ──────────────────────

async def _read_cache(pool: asyncpg.Pool, symbol: str, scan_date: date) -> list[Headline] | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT headlines FROM news_cache WHERE symbol = $1 AND cache_date = $2",
            symbol, scan_date,
        )
    if row is None:
        return None
    raw = row["headlines"]
    items = raw if isinstance(raw, list) else json.loads(raw)
    return [Headline(**h) for h in items]


async def _write_cache(pool: asyncpg.Pool, symbol: str, scan_date: date, headlines: list[Headline]) -> None:
    payload = json.dumps([h.as_dict() for h in headlines])
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO news_cache (symbol, cache_date, headlines, fetched_at)
            VALUES ($1, $2, $3::jsonb, now())
            ON CONFLICT (symbol, cache_date) DO UPDATE
              SET headlines = EXCLUDED.headlines,
                  fetched_at = now()
            """,
            symbol, scan_date, payload,
        )
