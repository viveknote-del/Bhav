# Bhav — Forward Plan

Product roadmap. Steps are the unit of work for `/pipeline`.
Use `/feature` to add new steps. Use `/next` to pick the next step to work on.

---

## Step 0 — Project Scaffold & Setup

**Depends on:** nothing
**Goal:** Working local dev environment — Postgres + Redis up, FastAPI health endpoint green, Next.js skeleton dashboard loads, CI passes.
**Added:** 2026-05-12

- [ ] Slim template: remove Supabase auth, profiles, login pages, RLS
- [ ] Docker Compose: Postgres 16 + Redis 7 (no Supabase)
- [ ] FastAPI scaffold: `main.py`, `config.py` (Pydantic settings), `dependencies.py`, `routers/health.py`
- [ ] Health endpoint returns DB + Redis + yfinance reachability
- [ ] asyncpg connection pool via `dependencies.py`
- [ ] Next.js dashboard skeleton page (`app/page.tsx` — "No scans yet")
- [ ] arq worker scaffold (`workers/__init__.py`, WorkerSettings)
- [ ] GitHub Actions CI: ruff + mypy + pytest backend, eslint + typecheck + vitest frontend
- [ ] `.env.example` complete, `Makefile` with `make dev`, `make test`, `make scan-now`
- [ ] README updated with setup steps

## Step 1 — Universe & Data Pipeline

**Depends on:** Step 0
**Goal:** NSE/BSE instruments loaded, daily bars fetchable and cached, browsing UI works.
**Added:** 2026-05-12

- [ ] `providers/market_data.py` abstract interface (`get_bars`, `get_quote`, `list_instruments`)
- [ ] `providers/yfinance_provider.py` impl (handles `.NS`/`.BO` suffixes, rate-limit backoff)
- [ ] One-time NSE 500 + BSE 500 instrument seeder (loads CSV → `instruments` table)
- [ ] `services/instrument_service.py` + `repositories/instrument_repo.py`
- [ ] Daily bar fetcher with cache-first lookup against `daily_bars`
- [ ] `GET /v1/instruments` (paginated, search, exchange filter)
- [ ] `GET /v1/charts/{symbol}?days=180`
- [ ] `POST /v1/instruments/refresh` (admin trigger)
- [ ] Frontend: instrument browser page with search + sector filter
- [ ] Unit tests: provider mock returns synthetic bars, service handles missing data

## Step 2 — Breakout Engine: 52w High + Volume Spike

**Depends on:** Step 1
**Goal:** EOD scan runs across the universe, detects 52-week highs and volume spikes, persists ranked breakouts.
**Added:** 2026-05-12

- [ ] `services/breakout/fifty_two_week.py` — pure detector function
- [ ] `services/breakout/volume_spike.py` — pure detector function
- [ ] `services/breakout/scoring.py` — composite score v1 (price_strength, volume_ratio, trend, ATR)
- [ ] `services/scan_service.py` — orchestrates universe iteration, batches yfinance fetches
- [ ] `repositories/scan_repo.py`, `repositories/breakout_repo.py`
- [ ] arq job: `workers/scan_eod.py` with `@job` decorator
- [ ] `POST /v1/scans` enqueues a scan; returns `scan_run_id` immediately
- [ ] `GET /v1/scans`, `GET /v1/scans/{id}`, `GET /v1/breakouts`
- [ ] Unit tests: detectors against synthetic bars (insufficient history, exact-tie, clear breakout)
- [ ] Integration test: full scan over 10-symbol fixture universe

## Step 3 — Breakout Engine: Consolidation & Patterns

**Depends on:** Step 2
**Goal:** Add consolidation breakouts and pattern detection (flag, cup-handle, triangle).
**Added:** 2026-05-12

- [ ] `services/breakout/consolidation.py` — 20-day Donchian + ATR-tightness
- [ ] `services/breakout/patterns.py` — flag, cup-and-handle, triangle (talipp + custom rules)
- [ ] Update scoring to include `pattern_quality` term
- [ ] `pattern_subtype` populated in `breakouts` table
- [ ] Backtest harness: replay 6 months of historical data, output detector hit rates
- [ ] Unit tests per pattern with hand-crafted bar sequences

## Step 4 — AI Commentary

**Depends on:** Step 3
**Goal:** Top-20 breakouts per scan get Claude-generated commentary with news context.
**Added:** 2026-05-12

- [ ] `providers/llm.py` — Claude Sonnet 4.6 wrapper, prompt caching on system + examples
- [ ] `providers/news.py` — NewsAPI client with `(symbol, date)` cache
- [ ] `prompts/registry.py` — versioned breakout commentary prompt + EOD digest prompt
- [ ] `services/commentary_service.py` — compose context (signal + indicators + headlines) → Claude
- [ ] arq job: `workers/commentary.py` — runs after `scan_eod` completes, processes top 20
- [ ] EOD digest job: writes a single "today's top 5" summary, stored in `scan_runs.summary` (add column)
- [ ] `POST /v1/breakouts/{id}/commentary` — manual regeneration
- [ ] Eval cases for commentary prompt (does it cite the actual indicators? does it hedge appropriately?)

## Step 5 — Dashboard UI

**Depends on:** Step 4
**Goal:** Polished single-page dashboard surfaces ranked breakouts with charts, commentary, news.
**Added:** 2026-05-12

- [ ] `app/page.tsx` — today's breakouts list, sorted by score, with filter chips
- [ ] Filter chips: breakout type, exchange, min score, sector
- [ ] Detail drawer: price chart (lightweight-charts, 180 days), indicator overlay, commentary, news links
- [ ] `app/scans/page.tsx` — scan history with mini stats per run
- [ ] `app/instruments/[symbol]/page.tsx` — per-symbol historical breakouts
- [ ] `app/watchlist/page.tsx` — CRUD watchlist
- [ ] EOD digest displayed prominently on home page
- [ ] Empty/loading/error states
- [ ] Responsive layout (desktop-first, mobile readable)

## Step 6 — Scheduling & Intraday Mode

**Depends on:** Step 5
**Goal:** Scans run automatically post-market; optional intraday loop during market hours.
**Added:** 2026-05-12

- [ ] arq cron: daily 15:35 IST EOD scan (Mon–Fri)
- [ ] NSE holiday calendar check before EOD scan
- [ ] Intraday loop: 5-min interval during 09:15–15:30 IST, gated by `INTRADAY_ENABLED` env
- [ ] `is_market_open()` utility with holiday + weekend handling
- [ ] Frontend: "Run scan now" button + live scan status indicator
- [ ] Telemetry: per-scan timings logged so we can spot slowdowns

## Step 7 — Alerts, Backtests & Polish

**Depends on:** Step 6
**Goal:** Get notified when high-conviction breakouts fire intraday; validate scoring against history; production-grade polish.
**Added:** 2026-05-12

*(Note: data provider stays yfinance throughout — see DOCS/DECISIONS.md #008 for rationale on not adding broker integration in v1.)*

- [ ] Alert channels: desktop notifications (local) + Telegram bot (optional)
- [ ] Alert rule: composite_score > 80 AND breakout_type in {52W_HIGH, CONSOLIDATION}
- [ ] Backtest harness: replay any date range, compute hit rate / mean forward return / win rate
- [ ] Backtest UI: pick date range + detector mix, see results table
- [ ] Frontend polish: keyboard shortcuts (j/k navigate, w add to watchlist), dark mode default
- [ ] E2E test (Playwright): trigger scan → see breakouts → open detail → commentary visible
- [ ] Production-readiness checklist: structured logging, error boundaries, healthcheck depth

---

*(Add more steps via `/feature` or manually)*
