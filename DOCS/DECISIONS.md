# Bhav — Architecture Decisions

Log of significant decisions — what was chosen, what was rejected, and why.

---

## 001 — Monorepo structure

**Decision:** Single pnpm monorepo (`apps/`, `services/`, `packages/`)
**Rejected:** Separate repos per service
**Reason:** Shared types, easier CI, atomic commits across layers

## 002 — Backend layering (Router → Service → Repository)

**Decision:** Strict 3-layer separation in FastAPI
**Reason:** Prevents direct DB calls from route handlers, enables unit testing without DB, makes layer swaps safe

## 003 — Job queue (arq over Celery)

**Decision:** arq for async jobs
**Rejected:** Celery, raw Redis Streams
**Reason:** Lightweight, Python-native, no broker config beyond Redis, type-safe task signatures

## 004 — All AI calls through providers/llm.py

**Decision:** Single abstraction layer for all LLM calls
**Reason:** Easy model swap, consistent retry logic, centralized cost tracking, prevents scattered direct SDK calls

---

## 005 — Drop Supabase, use local Postgres

**Decision:** Single local Postgres instance via docker compose. No Supabase, no auth, no RLS.
**Rejected:** Supabase (template default), SQLite
**Reason:** Bhav is a single-user personal tool running on localhost. Supabase's auth/RLS/realtime features add complexity for zero benefit. SQLite was tempting but Postgres handles JSONB (used for `indicators` and `news_links`) and concurrent worker writes more cleanly.

## 006 — Market data: yfinance for v1

**Decision:** yfinance (`.NS` for NSE, `.BO` for BSE) behind a pluggable `providers/market_data.py` interface.
**Rejected:** Zerodha Kite Connect (₹2000/month, requires Zerodha account), Motilal Oswal API, NSE scraping
**Reason:** Free, no account required, works today, decent EOD reliability, ~15-min delayed intraday is acceptable for a screener that runs post-market. The provider interface means we can swap later without touching detectors or services.

## 007 — News: NewsAPI free tier

**Decision:** NewsAPI free tier (100 req/day) with aggressive `(symbol, date)` caching.
**Rejected:** Scraping Moneycontrol/Economic Times, Google News RSS
**Reason:** Clean JSON API, decent India coverage. 100 req/day is tight but caching + only fetching for top-20-by-score breakouts keeps us well under quota.

## 008 — No broker API integration in v1 (defer Motilal Oswal / Upstox / Kite)

**Decision:** Stay on yfinance through Step 7. Broker API integration is out of scope.
**Rejected:** Motilal Oswal API (user has account), Upstox, Kite, Fyers
**Reason:** True real-time pricing matters for traders executing orders. For a screener that ranks breakouts and writes commentary, 15-min-delayed intraday is fine — by the time we've scored a signal and written commentary, the timing edge from sub-minute data is irrelevant. Adding broker auth, WebSocket handling, and reconnection logic doubles the surface area. If we later need real-time, the `market_data` interface makes it a one-file swap.

## 009 — TA library: ta + talipp

**Decision:** `ta` for pandas-native indicators (RSI, ATR, Bollinger, Donchian), `talipp` for streaming-style pattern matching.
**Rejected:** TA-Lib (C dependency, painful Windows install), pandas-ta (stale)
**Reason:** Both are pure-Python, no native build step, work cleanly on Windows. `talipp`'s incremental indicator computation is useful for the intraday loop.

## 010 — Charting: lightweight-charts (TradingView OSS)

**Decision:** TradingView's lightweight-charts library for price charts.
**Rejected:** Chart.js, Recharts, Highcharts
**Reason:** Made for financial OHLCV. Free, fast, looks like a real trading chart out of the box. Recharts/Chart.js need significant work to render candles cleanly.

## 011 — Composite score weighting

**Decision:** `score = 0.35 × price_strength + 0.25 × volume + 0.20 × pattern_quality + 0.10 × trend + 0.10 × atr_clean_break`
**Reason:** Empirical starting point. Step 7's backtest harness will let us tune these against historical hit rates. Weights live in `services/breakout/scoring.py` as constants — easy to grep, easy to change.

## 012 — Top-N filter before AI commentary

**Decision:** Only top 20 breakouts per scan get Claude commentary. The rest are stored without commentary.
**Reason:** A wide scan can surface 100+ breakouts; commenting on all of them burns Claude tokens for low-conviction signals nobody will read. Top 20 keeps cost predictable (~$0.10/scan) and quality high.

---

*(Add new decisions as they're made during pipeline runs)*
