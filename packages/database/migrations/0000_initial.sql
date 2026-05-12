-- Initial schema migration for Bhav
-- Created: 2026-05-12

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Stock universe (NSE + BSE listings, refreshed weekly)
CREATE TABLE IF NOT EXISTS instruments (
    symbol      TEXT PRIMARY KEY,                 -- e.g. 'RELIANCE.NS', 'TATAMOTORS.BO'
    exchange    TEXT NOT NULL CHECK (exchange IN ('NSE', 'BSE')),
    name        TEXT NOT NULL,
    sector      TEXT,
    industry    TEXT,
    market_cap  NUMERIC,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS instruments_exchange_idx ON instruments (exchange) WHERE is_active;
CREATE INDEX IF NOT EXISTS instruments_sector_idx   ON instruments (sector)   WHERE is_active;

-- Daily OHLCV cache (avoid re-fetching from yfinance)
CREATE TABLE IF NOT EXISTS daily_bars (
    symbol  TEXT NOT NULL REFERENCES instruments(symbol) ON DELETE CASCADE,
    date    DATE NOT NULL,
    open    NUMERIC NOT NULL,
    high    NUMERIC NOT NULL,
    low     NUMERIC NOT NULL,
    close   NUMERIC NOT NULL,
    volume  BIGINT  NOT NULL,
    PRIMARY KEY (symbol, date)
);

CREATE INDEX IF NOT EXISTS daily_bars_date_idx ON daily_bars (date DESC);

-- Each scan run (EOD or intraday)
CREATE TABLE IF NOT EXISTS scan_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    scan_type       TEXT NOT NULL CHECK (scan_type IN ('EOD', 'INTRADAY')),
    universe_size   INT,
    breakouts_found INT,
    status          TEXT NOT NULL CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED')),
    error           TEXT,
    summary         TEXT,                         -- Claude-generated EOD digest (Step 4)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS scan_runs_started_idx ON scan_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS scan_runs_status_idx  ON scan_runs (status) WHERE status = 'RUNNING';

-- Detected breakouts
CREATE TABLE IF NOT EXISTS breakouts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_run_id     UUID NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
    symbol          TEXT NOT NULL REFERENCES instruments(symbol) ON DELETE CASCADE,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    breakout_type   TEXT NOT NULL CHECK (breakout_type IN (
                        'FIFTY_TWO_WEEK_HIGH', 'CONSOLIDATION', 'VOLUME_SPIKE', 'PATTERN'
                    )),
    pattern_subtype TEXT CHECK (pattern_subtype IN ('FLAG', 'CUP_HANDLE', 'TRIANGLE')),
    price           NUMERIC NOT NULL,
    breakout_level  NUMERIC,                      -- the level it broke above
    volume_ratio    NUMERIC,                      -- today_vol / 20d_avg_vol
    composite_score NUMERIC NOT NULL,             -- 0-100
    indicators      JSONB,                        -- { rsi, atr, dist_from_52w_high, ... }
    ai_commentary   TEXT,
    news_links      JSONB,                        -- [{ title, url, source, published_at }]
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS breakouts_scan_idx     ON breakouts (scan_run_id);
CREATE INDEX IF NOT EXISTS breakouts_score_idx    ON breakouts (composite_score DESC);
CREATE INDEX IF NOT EXISTS breakouts_symbol_idx   ON breakouts (symbol, detected_at DESC);
CREATE INDEX IF NOT EXISTS breakouts_type_idx     ON breakouts (breakout_type);
CREATE INDEX IF NOT EXISTS breakouts_detected_idx ON breakouts (detected_at DESC);

-- Personal watchlist
CREATE TABLE IF NOT EXISTS watchlist (
    symbol      TEXT PRIMARY KEY REFERENCES instruments(symbol) ON DELETE CASCADE,
    notes       TEXT,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
