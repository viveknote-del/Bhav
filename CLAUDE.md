# {{PROJECT_DISPLAY_NAME}} — Project Context for Claude Code

> **Last Updated:** {{DATE}} | **Phase: Scaffold** | **{{TECH_STACK}}**

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

{{PROJECT_DESCRIPTION}}

### Core Flow

```
[describe the main user journey in 3-5 steps]
```

### Revenue Model

| Tier | Price | Features |
|---|---|---|
| Free | $0 | [features] |
| Growth | $X/month | [features] |
| Pro | $Y/month | [features] |

---

## Architecture Overview

### Services

| Service | Tech | Port |
|---|---|---|
| Frontend | Next.js 15 | 3000 |
| API | FastAPI | 8000 |
| PostgreSQL | Supabase Postgres | 5432 |
| Redis | Redis 7 | 6379 |

### System Diagram

```
┌─────────────────────────────────┐
│  Frontend (Next.js 15)          │
│  App Router, Supabase Auth      │
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│  Backend (FastAPI)              │
│  Router → Service → Repository  │
│           │                     │
│  ┌────────▼────────┐            │
│  │  arq Workers    │            │
│  └────────┬────────┘            │
└───────────┼─────────────────────┘
            │
┌───────────▼─────────────────────┐
│  Data Layer                     │
│  PostgreSQL  Redis  S3/Storage  │
└─────────────────────────────────┘
```

---

## FastAPI Architecture Conventions

**Hard rule: Router → Service → Repository → Supabase. No skipping layers.**

```python
# routers/items.py        — HTTP in/out, validation, auth guard
# services/item_service.py — business logic, orchestration
# repositories/item_repo.py — raw DB queries via supabase-py
```

- Routers never import repositories directly.
- Services never import other services (use dependency injection).
- Repositories return raw data; services transform to domain objects.
- All AI calls go through `providers/llm.py` — never call the LLM client directly from a router or service.

---

## File Map

### Frontend (`apps/web/src/`)

**Pages:** `app/page.tsx` (home), `app/(auth)/login/page.tsx`, `app/(app)/dashboard/page.tsx`

**Components:** `components/ui/` (Button, Card, Input), `components/` (feature components)

**Hooks:** `hooks/useAuth.ts`, `hooks/useData.ts`

**Lib:** `lib/api.ts` (axios + JWT), `lib/constants.ts` (API URLs), `lib/supabase.ts`

**Types:** `types/index.ts`

### Backend (`services/api/`)

`main.py` (app factory), `config.py` (Pydantic settings), `auth.py` (JWT), `dependencies.py` (FastAPI Depends)

**Routers:** `routers/health.py`, `routers/items.py`

**Services:** `services/item_service.py`

**Repositories:** `repositories/item_repo.py`

**Models:** `models/` (Pydantic request/response models)

**Workers:** `workers/` (arq async workers)

**Providers:** `providers/llm.py` (AI abstraction), `providers/image.py`

**Tests:** `tests/conftest.py`, `tests/test_*.py`

### Database (`packages/database/`)

Migrations: `0000_initial.sql`, `0001_*.sql`, ...

### Shared Types (`packages/shared-types/`)

`src/index.ts` — TypeScript types shared between frontend and any type-safe consumers.

---

## Development Commands

```bash
# Start local services
docker compose up -d

# Frontend dev
cd apps/web && pnpm dev

# Backend dev
cd services/api && uvicorn main:app --reload --port 8000

# Backend tests
cd services/api && pytest -v

# Frontend tests
cd apps/web && pnpm test

# E2E tests
cd apps/web && pnpm playwright test

# Full health check
./scripts/sanity-check.sh
```

---

## Environment Variables

See `.env.example` for all required variables.

Key variables:
```
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# API
API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000

# Redis
REDIS_URL=redis://localhost:6379

# AI (optional)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

---

## Pitfalls to Avoid

### API calls
- **Always use `apiClient`** — never bare `fetch()`. Plain `fetch()` sends no auth header.
- **Never hardcode localhost URLs** — use `lib/constants.ts` and env vars.

### Backend
- **`database.py` must use `SUPABASE_SERVICE_KEY`** — anon key causes RLS 42501 violations.
- **All AI calls through `providers/llm.py`** — never call the LLM SDK directly from business logic.
- **Repository functions return raw data** — services own transformation and validation.

### Frontend
- **Never use `"latest"` for dependencies** — pin exact versions. Tailwind is v3 (`3.4.x`), not v4.
- **Tailwind v3 only** — v4 requires Next.js 15.1+. Use `@tailwind` directives in globals.css.
- **Theme uses CSS custom properties** — use `var(--foreground)` not `dark:text-white`.

---



## Key Conventions (new projects must not skip these)

- **API routes: always `/v1/` prefix** — `router = APIRouter(prefix="/v1/items")`. Painful to add later.
- **Prompts: never inline strings** — all prompts live in `prompts/registry.py`. Bump version on change.
- **Evals: run before merging prompt changes** — `make evals`. CI blocks if score drops.
- **Workers: always use `@job` decorator** — never write a bare arq task. Silent failures are worse than loud ones.
- **Cost budget: check before AI endpoints** — `await check_budget(user_id, tier, redis)`.
- **Startup: validate env vars** — `main.py` raises on missing config. Don't add optional behavior for required vars.

## Token Hygiene

**This file loads on every session.** Every 100 lines = ~2,500 tokens burned before you type anything.

Hard limits:
- `CLAUDE.md` — 300 lines max. Trim before adding. Every section must earn its place.
- `DOCS/BUGS.md` — active bugs only. Resolved bugs → `/trim` archives them to `DOCS/BUGS-ARCHIVE.md`.
- `DOCS/KANBAN.md` — in-progress and backlog only. Completed steps → `/trim` archives them.
- `DOCS/pipeline/step-N/summary.md` — these ARE the AI cross-session memory. Never skip writing them.

Run `/trim` every 3-5 merged PRs. It takes 30 seconds and saves thousands of tokens per session.

Do NOT add architecture notes, decision logs, or pitfall discoveries to this file — they belong in
`ARCHITECTURE.md`, `DOCS/DECISIONS.md`, or the relevant step's `summary.md`.

## Agent Instructions

- **Always update this file** when completing tasks, fixing bugs, or making architectural decisions.
- **Always update [KANBAN.md](./DOCS/KANBAN.md)** when tasks move between columns.
- **Always update [ARCHITECTURE.md](./ARCHITECTURE.md)** when adding endpoints, services, or changing infrastructure.
- Skip generated directories: `node_modules`, `.next`, `__pycache__`, `.venv`, `dist`.
- Use `pnpm` for frontend, `pip`/`uv` for backend.

---

## Skill Routing

When the user's request matches a command, invoke it as your FIRST action.

### Custom commands

| Trigger | Command | When to use |
|---|---|---|
| "starting a new project", "plan the system" | `/kickoff` | Initial system design — architecture, schema, API, step plan |
| "what's next", "what should I work on" | `/next` | Prioritized menu of bugs, deferrals, steps |
| implement a step, build a feature | `/pipeline "Step N — Name"` | Full SDLC cycle for one step |
| "build the whole plan", "run everything" | `/orchestrate` | Multi-step orchestrator with human gates |
| "just go", "work through the backlog" | `/autopilot` | Continuous loop — picks and executes items |
| "build everything", "run overnight" | `/orchestrate --full-auto` | Zero-touch after plan approval — tests replace human review |
| found a bug | `/bug` | Triage and log to DOCS/BUGS.md |
| new feature idea | `/feature` | Interactive intake, writes into forward plan |
| PR open but session died | `/resume-pr` | Resume stalled pipeline from open PR |
| docs are bloated, trim context | `/trim` | Archive resolved bugs + completed KANBAN tasks |
| "what's happening", "check progress" | `/status` | Live orchestration dashboard |
| "stop", "pause orchestration" | `/halt` | Gracefully stop after current phase |

### Key routing rules

- "plan the system" / "design the architecture" → `/kickoff`
- "what's next" → `/next`
- "build step N" / single step → `/pipeline`
- "build everything" / "run the plan" → `/orchestrate`
- "build overnight" / "zero touch" → `/orchestrate --full-auto`
- "just go" / "work through it" → `/autopilot`
- "audit the design / UI" → `/design-review`
- "ship this" / "create a PR" → `/ship`
- "something is broken" → `/investigate`
- "docs are too long" / "trim" → `/trim`
- "what's the status" / "check progress" → `/status`
- "stop" / "pause" / "halt" → `/halt`

---

## Reference Docs

- **Task board:** [DOCS/KANBAN.md](./DOCS/KANBAN.md)
- **Bug tracker:** [DOCS/BUGS.md](./DOCS/BUGS.md)
- **Deferred items:** [DOCS/DEFERRED.md](./DOCS/DEFERRED.md)
- **Architecture:** [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Deployment:** [DOCS/DEPLOYMENT.md](./DOCS/DEPLOYMENT.md)
- **Decisions:** [DOCS/DECISIONS.md](./DOCS/DECISIONS.md)
- **Code standards:** [DOCS/CODE-STANDARDS.md](./DOCS/CODE-STANDARDS.md) ← read when implementing
- **Design patterns:** [DOCS/PATTERNS.md](./DOCS/PATTERNS.md) ← read when designing a feature
- **AI-first guide:** [DOCS/AI-FIRST.md](./DOCS/AI-FIRST.md)
- **Orchestration:** [DOCS/ORCHESTRATION.md](./DOCS/ORCHESTRATION.md) ← multi-step automation guide ← model routing, caching, evals, fallback
