# Bhav — Architecture

> **Last Updated:** 2026-05-12

## System Overview

Single-user Indian-stock breakout screener. Scheduled scanner fetches OHLCV data from yfinance, runs breakout detectors over the NSE/BSE universe, scores results, and generates Claude commentary for the top-ranked breakouts. Dashboard surfaces ranked results with price charts and news context.

## Services

| Service | Tech | Port | Hosting |
|---|---|---|---|
| Frontend | Next.js 15 (App Router) | 3000 | Local (Vercel later if exposed) |
| API | FastAPI | 8000 | Local |
| Database | Postgres 16 | 5432 | Local (docker compose) |
| Cache / Queue | Redis 7 | 6379 | Local (docker compose) |
| Worker | arq | — | Local |

## System Diagram

```
┌──────────────────────────────────────────┐
│  Next.js 15 Dashboard                    │
│  - Today's breakouts (ranked)            │
│  - Detail drawer (chart + commentary)    │
│  - Watchlist, scan history               │
└────────────────────┬─────────────────────┘
                     │ /v1/*
┌────────────────────▼─────────────────────┐
│  FastAPI                                 │
│  Router → Service → Repository           │
│                                          │
│  Services:                               │
│   - InstrumentService                    │
│   - ScanService (orchestrates detectors) │
│   - BreakoutService (detectors + score)  │
│   - CommentaryService                    │
│                                          │
│  Providers (abstractions):               │
│   - market_data (yfinance impl)          │
│   - llm (Claude impl, with caching)      │
│   - news (NewsAPI impl)                  │
└────────────────────┬─────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼─────────┐      ┌────────▼────────┐
│  arq workers    │      │  Postgres       │
│                 │      │                 │
│  - scan_eod     │      │  - instruments  │
│  - scan_intraday│◄─────┤  - daily_bars   │
│  - commentary   │      │  - scan_runs    │
│  - alerts       │      │  - breakouts    │
└───────┬─────────┘      │  - watchlist    │
        │                └─────────────────┘
        │
┌───────▼─────────┐
│  External APIs  │
│  - yfinance     │
│  - NewsAPI      │
│  - Anthropic    │
└─────────────────┘
```

## API Endpoints

All routes under `/v1/` prefix. No auth on v1 (single-user, localhost).

### Health
- `GET /v1/health` — DB + Redis + market data provider status

### Instruments
- `GET /v1/instruments` — paginated, query `?exchange=NSE|BSE&search=`
- `POST /v1/instruments/refresh` — re-fetch NSE/BSE listings (manual trigger)

### Scans
- `GET /v1/scans` — list scan runs, paginated
- `POST /v1/scans` — trigger ad-hoc scan, body `{ scan_type: "EOD"|"INTRADAY" }`
- `GET /v1/scans/{id}` — scan run detail with breakouts

### Breakouts
- `GET /v1/breakouts` — query `?date=&type=&min_score=&exchange=`, sorted by `composite_score DESC`
- `GET /v1/breakouts/{id}` — single breakout detail (commentary, news, indicators)
- `POST /v1/breakouts/{id}/commentary` — regenerate AI commentary

### Watchlist
- `GET /v1/watchlist`
- `POST /v1/watchlist` — body `{ symbol, notes }`
- `DELETE /v1/watchlist/{symbol}`

### Charts
- `GET /v1/charts/{symbol}` — query `?days=180`, returns OHLCV array

## Database Schema

See [packages/database/migrations/0000_initial.sql](./packages/database/migrations/0000_initial.sql) for the source of truth.

```sql
instruments       (symbol PK, exchange, name, sector, industry, market_cap, is_active, updated_at)
daily_bars        ((symbol, date) PK, open, high, low, close, volume)
scan_runs         (id PK, started_at, finished_at, scan_type, universe_size, breakouts_found, status)
breakouts         (id PK, scan_run_id FK, symbol FK, breakout_type, pattern_subtype, price,
                   breakout_level, volume_ratio, composite_score, indicators JSONB, ai_commentary,
                   news_links JSONB, detected_at, created_at)
watchlist         (symbol PK, notes, added_at)
job_results       (job_id PK, job_name, status, result, completed_at)         -- from 0001
failed_jobs       (id PK, job_id, job_name, args, kwargs, error, traceback, failed_at, replayed)
```

## Breakout Detection

### Detector Interface

All detectors are pure functions:

```python
def detect(symbol: str, bars: pd.DataFrame) -> Optional[BreakoutSignal]:
    """bars: indexed by date, columns [open, high, low, close, volume]
       Returns None if no breakout. Caller filters by score."""
```

### Detector Types

| Type | Logic |
|---|---|
| `FIFTY_TWO_WEEK_HIGH` | Today's close > max(close[-252:-1]) by ≥ 0.5%, volume > 1.5× 20d avg |
| `CONSOLIDATION` | 20-day Donchian channel break + ATR-normalized range tightness > threshold |
| `VOLUME_SPIKE` | Today's volume > 3× 20d avg with positive close, regardless of price level |
| `PATTERN` | Flag / cup-handle / triangle via talipp + custom geometric rules |

### Composite Score (0–100)

```
score = 0.35 × price_strength
      + 0.25 × volume_ratio_normalized
      + 0.20 × pattern_quality
      + 0.10 × trend_alignment (above 50d/200d MA)
      + 0.10 × atr_clean_break (break size vs ATR)
```

Top 20 breakouts per scan get AI commentary; the rest are stored but uncommentated.

## Scan Cadence

- **EOD scan:** arq cron, daily at 15:35 IST (Mon–Fri), excludes NSE holidays
- **Intraday scan:** optional 5-min loop during 09:15–15:30 IST, gated by `INTRADAY_ENABLED` env
- **Ad-hoc scan:** `POST /v1/scans` triggers immediate run

## Infrastructure Decisions

| Decision | Choice | Reason |
|---|---|---|
| Auth | None | Single-user, localhost-only |
| DB | Local Postgres (not Supabase) | No need for hosted auth/RLS/realtime |
| Queue | arq (Redis) | Lightweight, Python-native, typed tasks |
| Market data | yfinance | Free, no account, NSE + BSE coverage via `.NS`/`.BO` suffix |
| News | NewsAPI free tier | 100 req/day, decent India coverage; cache aggressively |
| AI | Claude Sonnet 4.6 via `providers/llm.py` | Prompt caching, single abstraction |
| Charts | lightweight-charts (TradingView OSS) | Free, fast, looks like a real trading chart |
| TA library | `ta` + `talipp` | pandas-friendly indicators + streaming-style patterns |
| Time zone | Store UTC, display IST | Standard practice |
