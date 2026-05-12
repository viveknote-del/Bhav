# Bhav — Project Context for Claude Code

> **Last Updated:** 2026-05-12 | **Phase: Scaffold** | **Next.js 15 + FastAPI + Postgres + Redis**

---

## Behavioral Guidelines

*Derived from Andrej Karpathy's observations on LLM coding pitfalls. These override any default behavior.*

### 1. Think Before Coding

**Don't assume. Surface tradeoffs. Ask before implementing.**

- State assumptions explicitly before writing code. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.
- Remove imports/variables/functions that **your** changes made unused. Leave pre-existing dead code alone.

Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria upfront. Loop until verified.**

Transform tasks into verifiable goals before starting:
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Add validation" → "Write tests for invalid inputs, then make them pass"

For multi-step tasks, state a brief plan with a verify step for each:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```

---

## Vision

**Bhav** is a single-user dashboard that scans NSE/BSE daily (and optionally intraday) for stock breakouts, ranks them, and shows Claude-generated commentary explaining *why* each one matters.

Not a SaaS. No auth, no tiers, no signups. Runs locally, scans the Indian market, surfaces signals worth investigating.

### Core Flow

```
1. Scanner runs (post-market 3:35 PM IST + optional 5-min intraday loop)
2. Detects 4 breakout types across NSE/BSE universe
3. Ranks results by composite score (price strength × volume × pattern quality)
4. Claude writes commentary per breakout, pulling news context from NewsAPI
5. User opens dashboard → sees ranked list → drills into chart + commentary + news
```

### Revenue Model

None. Personal tool.

---

## Architecture Overview

### Services

| Service | Tech | Port |
|---|---|---|
| Frontend | Next.js 15 | 3000 |
| API | FastAPI | 8000 |
| PostgreSQL | Local Postgres 16 | 5432 |
| Redis | Redis 7 | 6379 |
| Worker | arq | — |

### System Diagram

```
┌─────────────────────────────────┐
│  Frontend (Next.js 15)          │
│  Dashboard, charts, watchlist   │
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│  Backend (FastAPI)              │
│  Router → Service → Repository  │
│           │                     │
│  ┌────────▼────────┐            │
│  │  arq Workers    │            │
│  │  - EOD scan     │            │
│  │  - Intraday loop│            │
│  │  - AI commentary│            │
│  └────────┬────────┘            │
└───────────┼─────────────────────┘
            │
┌───────────▼─────────────────────┐
│  Data Layer                     │
│  Postgres   Redis               │
└─────────────────────────────────┘

External: yfinance (market data) │ NewsAPI (headlines) │ Claude (commentary)
```

---

## FastAPI Architecture Conventions

**Hard rule: Router → Service → Repository → Postgres. No skipping layers.**

```python
# routers/breakouts.py         — HTTP in/out, validation
# services/breakout_service.py — business logic, scoring
# repositories/breakout_repo.py — raw DB queries via asyncpg
```

- Routers never import repositories directly.
- Services never import other services (use dependency injection).
- Repositories return raw data; services transform to domain objects.
- All AI calls go through `providers/llm.py` — never call the LLM client directly from a router or service.
- All market data calls go through `providers/market_data.py` — never call yfinance directly from business logic.

---

## File Map

### Frontend (`apps/web/src/`)

**Pages:** `app/page.tsx` (today's breakouts), `app/scans/page.tsx` (scan history), `app/instruments/[symbol]/page.tsx` (chart + detail), `app/watchlist/page.tsx`

**Components:** `components/ui/` (Button, Card, Drawer), `components/breakout/` (BreakoutCard, BreakoutFilters), `components/chart/` (PriceChart using lightweight-charts)

**Lib:** `lib/api.ts` (axios client), `lib/constants.ts`

### Backend (`services/api/`)

`main.py`, `config.py`, `dependencies.py`

**Routers:** `routers/health.py`, `routers/instruments.py`, `routers/scans.py`, `routers/breakouts.py`, `routers/watchlist.py`, `routers/charts.py`

**Services:** `services/instrument_service.py`, `services/scan_service.py`, `services/breakout/` (detectors: `fifty_two_week.py`, `consolidation.py`, `volume_spike.py`, `patterns.py`, `scoring.py`)

**Repositories:** `repositories/instrument_repo.py`, `repositories/bar_repo.py`, `repositories/scan_repo.py`, `repositories/breakout_repo.py`

**Workers:** `workers/scan_eod.py`, `workers/scan_intraday.py`, `workers/commentary.py`

**Providers:** `providers/llm.py`, `providers/market_data.py` (interface) + `providers/yfinance_provider.py`, `providers/news.py`

**Prompts:** `prompts/registry.py` (versioned breakout commentary + EOD digest prompts)

### Database (`packages/database/migrations/`)

`0000_initial.sql` (instruments, daily_bars, scan_runs, breakouts, watchlist), `0001_job_tracking.sql`

---

## Development Commands

```bash
# Start local services
docker compose up -d

# Frontend dev
cd apps/web && pnpm dev

# Backend dev
cd services/api && uvicorn main:app --reload --port 8000

# Worker
cd services/api && arq workers.WorkerSettings

# Trigger a one-off scan
curl -X POST http://localhost:8000/v1/scans

# Backend tests
cd services/api && pytest -v
```

---

## Environment Variables

See `.env.example` for all required variables. Key ones:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bhav
REDIS_URL=redis://localhost:6379

# Market data (yfinance has no key)
MARKET_DATA_PROVIDER=yfinance

# AI
ANTHROPIC_API_KEY=

# News
NEWSAPI_KEY=

# Scan config
SCAN_UNIVERSE=NSE_500          # NSE_500 | NSE_ALL | NIFTY_50
INTRADAY_ENABLED=false
```

---

## Pitfalls to Avoid

### Market data
- **Always use `providers/market_data.py`** — never `import yfinance` directly in services or workers.
- **yfinance is rate-limited** — batch requests, cache to `daily_bars` table aggressively.
- **NSE tickers use `.NS` suffix, BSE uses `.BO`** — `instruments.symbol` stores the full suffixed form.
- **Indian market hours: 9:15 AM – 3:30 PM IST.** Intraday loop must check `is_market_open()` before running.

### Breakout detection
- **Detectors must be pure functions** — `(symbol, bars: pd.DataFrame) -> Optional[BreakoutSignal]`. No DB access inside.
- **Always require minimum bar history** (default: 250 trading days for 52w calculations). Skip and log if insufficient.
- **Score before AI commentary** — don't burn Claude tokens commenting on low-score breakouts. Filter to top N first.

### AI
- **All Claude calls through `providers/llm.py`** with prompt caching enabled (instructions section + few-shot examples cached).
- **Commentary prompts live in `prompts/registry.py`** with version bumps on change. Never inline prompt strings.
- **NewsAPI free tier = 100 req/day.** Cache headlines per (symbol, date) so reruns don't burn quota.

### Frontend
- **Tailwind v3** — not v4. Pin exact versions.
- **No `"latest"` in package.json.**
- **Use `lib/api.ts` for all backend calls** — never bare `fetch()`.

---

## Key Conventions

- **API routes: always `/v1/` prefix** — `router = APIRouter(prefix="/v1/breakouts")`.
- **Prompts: never inline strings** — all prompts live in `prompts/registry.py`. Bump version on change.
- **Workers: always use `@job` decorator** — never write a bare arq task.
- **Startup: validate env vars** — `main.py` raises on missing config.
- **Time zone: store all timestamps as UTC.** Display in IST on frontend.

## Token Hygiene

**This file loads on every session.** Every 100 lines = ~2,500 tokens burned before you type anything.

Hard limits:
- `CLAUDE.md` — 300 lines max. Trim before adding.
- `DOCS/BUGS.md` — active bugs only. Resolved → `/trim` archives.
- `DOCS/KANBAN.md` — in-progress and backlog only. Completed → `/trim` archives.
- `DOCS/pipeline/step-N/summary.md` — cross-session memory. Never skip writing them.

Run `/trim` every 3-5 merged PRs.

Do NOT add architecture notes, decision logs, or pitfall discoveries to this file — they belong in `ARCHITECTURE.md`, `DOCS/DECISIONS.md`, or the relevant step's `summary.md`.

## Agent Instructions

- **Always update this file** when completing tasks, fixing bugs, or making architectural decisions.
- **Always update [KANBAN.md](./DOCS/KANBAN.md)** when tasks move between columns.
- **Always update [ARCHITECTURE.md](./ARCHITECTURE.md)** when adding endpoints, services, or changing infrastructure.
- Skip generated directories: `node_modules`, `.next`, `__pycache__`, `.venv`, `dist`.
- Use `pnpm` for frontend, `pip`/`uv` for backend.

---

## Skill Routing

When the user's request matches a command, invoke it as your FIRST action.

| Trigger | Command | When to use |
|---|---|---|
| "starting a new project", "plan the system" | `/kickoff` | Initial system design |
| "what's next", "what should I work on" | `/next` | Prioritized menu |
| implement a step, build a feature | `/pipeline "Step N — Name"` | Full SDLC cycle for one step |
| "build the whole plan", "run everything" | `/orchestrate` | Multi-step orchestrator |
| "just go", "work through the backlog" | `/autopilot` | Continuous loop |
| found a bug | `/bug` | Triage and log to DOCS/BUGS.md |
| new feature idea | `/feature` | Interactive intake |
| docs are bloated | `/trim` | Archive resolved bugs + completed KANBAN |
| "what's happening" | `/status` | Orchestration dashboard |
| "stop", "pause" | `/halt` | Gracefully stop |

---

## Reference Docs

- **Task board:** [DOCS/KANBAN.md](./DOCS/KANBAN.md)
- **Bug tracker:** [DOCS/BUGS.md](./DOCS/BUGS.md)
- **Architecture:** [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Decisions:** [DOCS/DECISIONS.md](./DOCS/DECISIONS.md)
- **Forward plan:** [plans/forward.md](./plans/forward.md)
- **Code standards:** [DOCS/CODE-STANDARDS.md](./DOCS/CODE-STANDARDS.md)
- **Patterns:** [DOCS/PATTERNS.md](./DOCS/PATTERNS.md)
