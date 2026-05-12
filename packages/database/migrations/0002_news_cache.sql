-- News headline cache, keyed by (symbol, scan_date).
-- We aggressively cache because NewsAPI free tier is 100 req/day.
-- Created: 2026-05-12

CREATE TABLE IF NOT EXISTS news_cache (
    symbol      TEXT NOT NULL,
    cache_date  DATE NOT NULL,                    -- the date of the scan that fetched these
    headlines   JSONB NOT NULL,                   -- [{ title, url, source, published_at }, ...]
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, cache_date)
);

CREATE INDEX IF NOT EXISTS news_cache_fetched_idx ON news_cache (fetched_at DESC);
