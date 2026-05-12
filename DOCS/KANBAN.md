# Bhav — Kanban

> Last updated: 2026-05-12 | **All 8 steps complete 🎉**

## Backlog

*(empty — initial roadmap fully shipped)*

## In Progress

*(none)*

## Done

- [x] **Step 0** — Scaffold & Setup — 2026-05-12 — Postgres+Redis up on ports 5434/6381, Supabase auth stripped, `/v1/health` wired
- [x] **Step 1** — Universe & Data Pipeline — 2026-05-12 — `MarketDataProvider` interface + yfinance impl, NIFTY 50 seed, asyncpg pool, `GET /v1/instruments`, `GET /v1/charts/{symbol}`, `POST /v1/instruments/refresh`, frontend browser page
- [x] **Step 2** — Breakout Engine: 52w High + Volume Spike — 2026-05-12 — pure detector functions, composite scoring, scan orchestration, arq worker, `POST /v1/scans`, `GET /v1/scans`, `GET /v1/breakouts`
- [x] **Step 3** — Breakout Engine: Consolidation & Patterns — 2026-05-12 — Donchian-based consolidation, flag/cup-handle/triangle pattern detectors, `pattern_quality` baked into composite score, backtest harness with CLI (`make backtest START=… END=…`)
- [x] **Step 4** — AI Commentary — 2026-05-12 — `providers/llm.py` (AsyncAnthropic with prompt caching + cost tracking), `providers/news.py` (NewsAPI with `(symbol, date)` cache), versioned `prompts/registry.py`, commentary service, arq `commentary_for_scan` job (auto-enqueued after scan), EOD digest, `POST /v1/breakouts/{id}/commentary`, evals
- [x] **Step 5** — Dashboard UI — 2026-05-12 — Watchlist API (`GET/POST/DELETE /v1/watchlist`), top nav, home page with today's breakouts + EOD digest + filters, breakout detail page (TradingView lightweight-charts candle chart + indicators + AI commentary + news + watchlist toggle + manual regen), scans history, watchlist CRUD
- [x] **Step 6** — Scheduling & Intraday Mode — 2026-05-12 — `market_hours.py` (IST-aware `is_trading_day`/`is_market_open`), bundled `holidays.py` (NSE 2026, with verify-annually note), arq cron `eod_scan_cron` at 10:05 UTC / 15:35 IST Mon–Fri (skips holidays) + `intraday_scan_cron` every 5 min gated by `INTRADAY_ENABLED` + market hours; home page polls every 4s when scan is `RUNNING`; scan telemetry now logs `fetch_ms`/`persist_ms`/`total_ms`
- [x] **Step 7** — Alerts, Backtests & Polish — 2026-05-12 — Telegram alert provider + service (rule: `composite_score ≥ ALERT_MIN_SCORE` AND type in {52W_HIGH, CONSOLIDATION} AND `alerted_at IS NULL`), wired into `commentary_for_scan` worker; backtest API (`POST /v1/backtests`) + frontend page with date range and forward/win knobs; Nav adds Backtest link; Playwright `scan-flow.spec.ts` (home → detail, scans, watchlist) with auto-skip when prereqs missing; migration 0003 adds `alerted_at` to breakouts
