# kickoff — Initial system design and project planning

Guides you from "I have a product idea" to a fully planned, ready-to-execute
project with architecture, database schema, API surface, and step breakdown.

Run this ONCE when starting a new project. Everything after this uses
`/orchestrate` or `/pipeline` to execute.

## Usage

```
/kickoff "AI marketing agency for event organizers"
/kickoff                   ← interactive mode, asks questions
```

---

## Instructions

### Phase 1 — Product discovery (interactive, 1 round of questions)

If the user provided a description, use it as a starting point.
If not, ask: "What are you building? One paragraph is fine."

After hearing the idea, ask these questions in a SINGLE message.
Skip any that are already answered by the description:

```
Let me understand the product before designing the system.

1. **Core flow** — Walk me through the main user journey in 3-5 steps.
   (e.g., "User signs up → creates campaign → AI generates copy → user reviews → publishes")

2. **User types** — Who uses this? List the distinct roles.
   (e.g., host, attendee, admin, API consumer)

3. **Revenue model** — How does this make money?
   (e.g., freemium with 3 tiers, transaction fee, subscription)

4. **MVP scope** — What's the minimum you'd ship in 2-4 weeks?
   (e.g., "Just the core flow for one platform, no payments yet")

5. **Integrations** — What external services does it need?
   (e.g., Stripe, Resend, Instagram API, Claude API, S3)

6. **Existing work** — Is there prior art, a competitor to study, or existing code?
   (e.g., "Similar to Mailchimp but for events" or "I have a Figma mockup")

7. **Constraints** — Any hard constraints?
   (e.g., "Must work offline", "HIPAA compliant", "Solo developer", "Launch by June 6")
```

Wait for user answers before proceeding.

### Phase 2 — Architecture design

Based on the answers, design the system architecture. Use the `blueprint` gstack skill
if available, otherwise design manually.


#### 2A-pre — Design reference extraction (optional)

If the user says 'I want it to look like [URL]' or 'use [competitor] as a reference':

```bash
npx designlang <url> --out ./design-tokens --screenshots
```

Read the output files:
- \`./design-tokens/*-tailwind.config.js\` -> merge into \`apps/web/tailwind.config.ts\`
- \`./design-tokens/*-variables.css\` -> merge into \`apps/web/src/app/globals.css\`
- \`./design-tokens/*-design-language.md\` -> reference during frontend tasks

If no reference URL: skip this step.

#### 2A — Tech stack decisions

Present the recommended stack as a table:

```
Based on your requirements, here's the recommended stack:

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 15 (App Router) | SSR, React ecosystem, Vercel deployment |
| Backend | FastAPI | Async, auto-docs, Python AI ecosystem |
| Database | Supabase (Postgres) | Auth, RLS, Storage, Realtime built in |
| Queue | arq (Redis) | Lightweight, Python-native, typed tasks |
| Auth | Supabase Auth (GoTrue) | JWT, magic links, OAuth — no custom auth |
| AI | Claude via providers/llm.py | Best coding model, prompt caching |
| Images | Replicate / fal.ai | Flux models, async generation |
| Email | Resend | Simple API, React email templates |
| Hosting | Vercel (web) + Render (API) | Free tier, auto-deploy from GitHub |
| Storage | Supabase Storage | Integrated with auth and RLS |

Any changes? I can swap anything before we proceed.
```

Wait for user confirmation. Log decisions to `DOCS/DECISIONS.md`.

#### 2B — Data model design

Design the core database tables. Present as SQL DDL:

```sql
-- Core tables (MVP)

CREATE TABLE [main_entity] (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- [Additional tables based on the core flow]
```

Rules:
- Every table gets `id UUID`, `created_at`, `updated_at`
- Foreign keys with `ON DELETE CASCADE` for owned entities
- `status` columns use CHECK constraints with explicit allowed values
- RLS enabled on all tables
- Indexes on foreign keys and status columns

Present to user: "Here's the initial schema. We can evolve it — this is just step 0."

#### 2C — API surface design

Design the main endpoints:

```
## API Endpoints (MVP)

### Auth (Supabase-managed)
POST   /auth/signup
POST   /auth/login
POST   /auth/logout
GET    /auth/session

### [Main domain] (/v1/)
GET    /v1/[entities]              ← list with pagination
POST   /v1/[entities]              ← create
GET    /v1/[entities]/{id}         ← get by ID
PATCH  /v1/[entities]/{id}         ← update
DELETE /v1/[entities]/{id}         ← delete

### [Secondary domain]
[endpoints]

### Health
GET    /v1/health                  ← dependency status check
```

Rules:
- All routes under `/v1/` prefix
- List endpoints return `{ items: [], total, page, limit }`
- All mutations require auth (except health and public reads)
- Follow Router → Service → Repository layering

#### 2D — System diagram

Draw an ASCII architecture diagram:

```
┌─────────────────────────────┐
│  Frontend (Next.js 15)      │
│  Dashboard, Forms, Auth     │
└─────────────┬───────────────┘
              │
┌─────────────▼───────────────┐
│  Backend (FastAPI)          │
│  /v1/ REST API              │
│         │                   │
│  ┌──────▼──────┐            │
│  │ arq Workers │            │
│  └──────┬──────┘            │
└─────────┼───────────────────┘
          │
┌─────────▼───────────────────┐
│  Data Layer                 │
│  Postgres  Redis  Storage   │
└─────────────────────────────┘
```

Present the full architecture. Wait for user feedback.

### Phase 3 — Step decomposition

Break the project into 5-10 implementable steps. Each step should be:
- Completable in 1-3 pipeline runs (~2-8 hours of agent time)
- Independently testable
- Has clear acceptance criteria

Standard decomposition pattern:

```markdown
## Step 0 — Project Scaffold & Setup
**Depends on:** nothing
**Goal:** Working local dev, CI green, health endpoint, basic auth
- Monorepo setup (pnpm, Next.js, FastAPI)
- Docker Compose (Postgres + Redis)
- Supabase project + initial migration
- Health endpoint with dependency checks
- CI (lint, type-check, test)

## Step 1 — Authentication & Profiles
**Depends on:** Step 0
**Goal:** Users can sign up, log in, have a profile
- Supabase Auth integration
- JWT verification in FastAPI
- Profile table + auto-create trigger
- Login/signup pages
- useAuth hook + protected routes

## Step 2 — [Core Domain CRUD]
**Depends on:** Step 1
**Goal:** [Main entity] CRUD with full API + UI
- [Entity] table + migration
- Router → Service → Repository
- List page with pagination
- Create/edit form
- Detail page

## Step 3 — [Secondary Feature]
**Depends on:** Step 2
**Goal:** [Next most important feature]
- ...

## Step 4 — [AI Features / Workers]
**Depends on:** Step 2
**Goal:** Background AI generation
- arq worker setup
- prompts/registry.py with eval cases
- Generation endpoint (enqueue job)
- Status polling / SSE streaming
- Review UI

## Step 5 — [Integration / Publishing]
**Depends on:** Step 4
**Goal:** [External service integration]
- OAuth flow for [service]
- Publishing worker
- Status tracking

## Step 6 — [Payments / Monetization]
**Depends on:** Step 2
**Goal:** Subscription tiers and billing
- Stripe integration
- Tier enforcement middleware
- Billing dashboard

## Step 7 — [Polish & Launch]
**Depends on:** Steps 5, 6
**Goal:** Production-ready
- Error boundaries + loading states
- SEO (meta tags, OG images)
- Performance audit (Lighthouse)
- E2E test suite
- Production deployment
```

Present the step breakdown. Ask:
"Does this order make sense? Want to add, remove, or reorder anything?"

Wait for confirmation.

### Phase 4 — Write all project files

After user confirms the plan, write everything:

#### 4A — plans/forward.md
Write the full step breakdown with `Depends on:`, `Goal:`, and bullet points.

#### 4B — CLAUDE.md
Update these sections (preserve the behavioral guidelines and conventions — only update the project-specific parts):
- **Vision** — product description, core flow, revenue model
- **Architecture Overview** — services table, system diagram
- **File Map** — planned structure based on the steps
- **Pitfalls to Avoid** — any domain-specific gotchas from the discovery phase
- **Key Decisions** — link to DOCS/DECISIONS.md

Keep CLAUDE.md under 300 lines. Put detailed architecture in ARCHITECTURE.md.

#### 4C — ARCHITECTURE.md
Write the full architecture doc:
- System diagram
- Service table
- Database schema (full DDL from Phase 2B)
- API endpoints (from Phase 2C)
- Infrastructure decisions

#### 4D — DOCS/DECISIONS.md
Append tech stack decisions from Phase 2A:
```markdown
## 001 — Frontend: Next.js 15
**Decision:** Next.js 15 with App Router
**Rejected:** Remix, SvelteKit, plain React
**Reason:** [from discovery]
```

#### 4E — DOCS/KANBAN.md
Write the step list:
```markdown
# [Project] — Kanban

> Last updated: [date] | **Step 0 READY**

## Backlog
- [ ] **Step 0** — Scaffold *(depends: nothing)* — READY
- [ ] **Step 1** — Auth *(depends: Step 0)*
- [ ] **Step 2** — Core domain *(depends: Step 1)*
...

## In Progress

## Done
```

#### 4F — packages/database/migrations/0000_initial.sql
Write the initial migration from Phase 2B.

#### 4G — .env.example
Update with all required env vars from the tech stack decisions.

#### 4H — Commit everything

```bash
git add -A
git commit -m "docs: initial system design — architecture, schema, API surface, step plan"
```

### Phase 5 — Launch readiness check

Print the final summary:

```
=== Project Planned ===

Vision: [one sentence]
Steps: [N] steps, estimated [X-Y] hours of agent time
Architecture: [frontend] + [backend] + [database]
First step: Step 0 — Scaffold & Setup

Files written:
  ✓ plans/forward.md           — [N] steps with dependencies
  ✓ CLAUDE.md                  — project context updated
  ✓ ARCHITECTURE.md            — system diagram, schema, endpoints
  ✓ DOCS/DECISIONS.md          — [N] tech decisions logged
  ✓ DOCS/KANBAN.md             — step board ready
  ✓ packages/database/migrations/0000_initial.sql — initial schema

To start building:
  /pipeline "Step 0 — Scaffold & Setup"     ← one step at a time
  /orchestrate                              ← guided multi-step
  /orchestrate --full-auto                  ← full autopilot
```
