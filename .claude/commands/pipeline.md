# SDLC Pipeline (ECC-Powered)

Execute a full SDLC cycle for one kanban task using proven ECC skills at every phase.
One task at a time. Depth over breadth.

## How to invoke
```
/pipeline "Step 1 — Project Scaffold & Setup"
/pipeline "Step 3 — Core API Endpoints"
/pipeline "Step 4a — Background Workers"
```

Pass the exact step name from `plans/forward.md`.

## Docs folder per step

Every pipeline run writes all its docs into a dedicated folder:
```
DOCS/pipeline/step-{N}/
  requirements.md   ← Phase 1
  design.md         ← Phase 2
  journeys.md       ← Phase 3 Step 1
  issues.md         ← Phase 3 (ongoing — blockers, deferrals, tech debt)
  fix-log.md        ← Phase 3+ (every fix committed during this step)
  checkpoint.md     ← Updated at every phase transition — resume state if session dies
  testing.md        ← Phase 6C (local verification guide — written before PR review)
  summary.md        ← Phase 7D (post-merge)
```

Global running logs (accumulate across all steps):
```
DOCS/DEFERRED.md      ← items intentionally punted to a later step
DOCS/BUGS.md          ← post-merge bugs reported by user
DOCS/BACKLOG.md       ← feature requests
DOCS/REGRESSION.md    ← cross-step smoke test definitions
```

## Model routing (follow exactly)

| Phase | Model | Reason |
|---|---|---|
| Phase 0 — Context load | sonnet | File reads, git checks — no reasoning needed |
| Phase 1 — Requirements | opus | Deep product thinking, edge case discovery |
| Phase 2 — System design | opus | Architecture decisions, API contracts, DB schema |
| Phase 3 — Implementation (routine) | haiku | CRUD, migrations, models, tests — haiku handles these well at ~20x lower cost |
| Phase 3 — Implementation (on failure) | opus | CI failure, build error, or test failure — escalate to opus |
| Phase 4 — PR creation | sonnet | PR writing, git ops |
| Phase 5 — Review + fix | sonnet | Fast iteration on code fixes |
| Phase 6 — Verification | sonnet | Test runs, smoke tests, writing testing.md |
| Phase 7 — Merge + docs | sonnet | Post-merge docs, KANBAN update |

### Phase 3 escalation rule (Haiku → Opus)

```
FOR EACH implementation task in Phase 3:
  1. Spawn agent with model: "haiku" to implement the task
  2. Run tests / build
  3. IF tests pass AND build green:
       → commit, continue to next task with haiku
  4. IF tests fail OR build errors:
       → spawn agent with model: "opus" to diagnose and fix
       → re-run tests
       → IF green: commit, resume haiku for next task
       → IF still failing after opus: STOP — surface to user
```

**What haiku handles (routine):**
- CRUD endpoints (routers, services, repositories)
- DB migrations and model definitions
- Unit and integration tests
- Frontend hooks and fetch wrappers
- Pydantic model definitions

**What triggers opus escalation:**
- `pytest` exits non-zero (any test failure)
- `pnpm build` exits non-zero
- `pnpm lint` exits non-zero with errors
- CI check fails on the PR
- A haiku agent produces code that another haiku agent cannot fix in one pass

---

## Phase 0 — Load Context (no agents, no skills)

YOU (main session) do this manually before anything else:

1. Read `plans/forward.md` — locate the section for the step name passed in
2. Read `DOCS/KANBAN.md` — if this step is already marked DONE, stop and tell the user
3. Read `CLAUDE.md` — reload all project constraints
4. Read `ARCHITECTURE.md` — understand current system shape
5. Read `DOCS/DEFERRED.md` if it exists — check if any deferred items from prior steps are now due
6. Read all existing `DOCS/pipeline/step-*/summary.md` files — compressed memory of every completed step
7. Run `git status` — must be clean. If dirty, stop and tell the user to commit or stash first
8. Run `git checkout main && git pull origin main`
9. Start local services:
   ```bash
   docker compose up -d
   # If using Supabase local: supabase start
   ```
10. Run `mkdir -p DOCS/pipeline/step-{N}`
11. Run `git checkout -b feat/step-{N}-{slug}`
12. Read `DOCS/BUGS.md` if it exists — P0/P1 bugs targeting this step become mandatory acceptance criteria
13. Read `DOCS/BACKLOG.md` if it exists — feature requests assigned to this step
14. Read `DOCS/REGRESSION.md` if it exists — run these smoke tests in Phase 6
15. Read `DOCS/pipeline/step-{N}/checkpoint.md` if it exists — do not redo completed phases
16. Read `DOCS/pipeline/step-{N}/fix-log.md` if it exists — do not re-fix what is already fixed

**DEFERRED.md deferral limit rule:** If any item has been deferred 3 or more times, it must be addressed in this step regardless of original target.

Do not proceed until all 16 pass.

---

## Phase 1 — Requirements (ECC Skill: product-capability)

Load the `product-capability` skill. Feed it:
- The full text of the matching step from `plans/forward.md`
- The CLAUDE.md constraints section
- This instruction:

```
Apply the product-capability skill to produce a requirements manifest for this
one step only. Output must be granular enough that a non-technical person could
understand exactly what will be built, and an implementing agent cannot
miss or misinterpret a single detail.

Required sections:
- Capability summary (1 paragraph)
- User stories (who does what and why)
- Acceptance criteria (binary pass/fail per feature)
- API contracts (endpoint, method, request body, response shape, error codes)
- DB changes (tables, columns, constraints, migrations needed)
- Non-goals (what is explicitly out of scope for this step)
- Open questions (unresolved ambiguities — must be answered before Phase 2)
```

Write the output to `DOCS/pipeline/step-{N}/requirements.md`.

Update `DOCS/pipeline/step-{N}/checkpoint.md`:
```
Phase 1 complete: requirements.md written
Open questions: [list any — must be resolved before Phase 2]
```

---

## Phase 2 — System Design (ECC Skill: blueprint or api-design)

Use the `blueprint` skill for new features. Use `api-design` when the step is primarily new API endpoints.

Feed it:
- `DOCS/pipeline/step-{N}/requirements.md`
- `ARCHITECTURE.md`
- Current file structure (tree of relevant directories)

Required output sections:
- Component diagram (which files change, which are new)
- API contract (exact endpoint signatures, types, error codes)
- DB migration plan (exact SQL, column types, constraints, indexes)
- Sequence diagrams for non-trivial flows
- Edge cases and failure modes addressed
- Test plan outline (what unit, integration, and E2E tests will cover)

Write the output to `DOCS/pipeline/step-{N}/design.md`.

Update `checkpoint.md`:
```
Phase 2 complete: design.md written
```

---

## Phase 3 — Implementation

**Model: haiku by default. Escalate to opus on any failure.**

### Phase 3A — User journeys (main session, before spawning agents)

Write `DOCS/pipeline/step-{N}/journeys.md`:

For each user story in requirements.md, write the complete expected UI and API flow.
This file is read by the implementing agent to understand what "done" looks like from the user's perspective.

### Phase 3B — Spawn implementing agents

Spawn one agent per implementation task from design.md:

```
For each task:
  Agent(model="haiku", prompt="
    Read DOCS/pipeline/step-{N}/design.md and DOCS/pipeline/step-{N}/journeys.md.
    Read CLAUDE.md for project conventions.
    Implement: [specific task from design.md]
    
    Follow the FastAPI layer conventions in CLAUDE.md:
      - Routers never import repositories
      - All AI calls through providers/llm.py
      
    After implementing:
    1. Run: pytest services/api/tests/ -v (or pnpm test)
    2. If tests pass → report done with commit SHA
    3. If tests fail → fix once, re-run, report status
    
    Write any blockers or tech debt to DOCS/pipeline/step-{N}/issues.md
  ")
```

Log each commit to `DOCS/pipeline/step-{N}/fix-log.md`:
```
{timestamp} {commit-sha}: {what was implemented}
```

### Phase 3C — Integration check

After all agents complete:
```bash
# Backend
pytest services/api/tests/ -v --tb=short

# Frontend
cd apps/web && pnpm build && pnpm test

# Docker sanity
docker compose up -d && ./scripts/sanity-check.sh
```

If anything fails → escalate to opus to diagnose and fix. Log the fix.

---

## Phase 4 — Create PR (ECC Skill: ship)

Load the `ship` skill.

Before creating the PR, run the pre-PR checklist:
```bash
# All tests green?
pytest services/api/tests/ -v && cd apps/web && pnpm test

# No TypeScript errors?
cd apps/web && pnpm tsc --noEmit

# Lint clean?
cd apps/web && pnpm lint
```

Create the PR:
```bash
gh pr create \
  --title "feat(step-{N}): {step name}" \
  --base main \
  --body "$(cat DOCS/pipeline/step-{N}/design.md)"
```

PR body should include:
- What was built (from journeys.md)
- Key technical decisions (from design.md)
- Deferred items (from issues.md)
- Test plan (how to verify — from testing plan in design.md)

Update `checkpoint.md`:
```
Phase 4 complete: PR #{N} opened
```

---

## Phase 5 — Code Review (ECC Skill: review)

Load the `review` skill. Feed it the PR diff:
```bash
git diff main...HEAD
```

Address all CRITICAL and HIGH findings before proceeding.
MEDIUM findings: fix if < 30 min, otherwise log to issues.md as tech debt.
LOW findings: log to issues.md, fix in a future step.

For each fix:
1. Make the change
2. Commit: `git commit -m "fix(step-{N}): [what was fixed]"`
3. Push: `git push origin feat/step-{N}-{slug}`
4. Log to fix-log.md

---

## Phase 6 — Verification

### Phase 6A — Run regression tests

Read `DOCS/REGRESSION.md`. Run all smoke tests defined there. Log any failures.

### Phase 6B — Run new tests

```bash
# All backend tests
pytest services/api/tests/ -v

# Frontend tests
cd apps/web && pnpm test

# E2E (if applicable)
cd apps/web && pnpm playwright test
```

If any test fails → fix, commit, push, re-run.

### Phase 6C — Write testing.md

Write `DOCS/pipeline/step-{N}/testing.md` — a local verification guide for a human reviewer:

```markdown
# Step N — Testing Guide

## Setup
[prerequisites — running services, env vars]

## Backend tests
[copy-pasteable commands with specific expected output]

## Frontend tests
[copy-pasteable commands]

## Manual smoke tests
[step-by-step UI flows to verify visually]

## What is NOT tested
[honest list of gaps — what regression could slip through]
```

Update `checkpoint.md`:
```
Phase 6 complete: all tests passing, testing.md written
```

---

## Phase 7 — Post-merge docs

**CRITICAL: Write all docs on the feature branch BEFORE merging. Docs must land on main through the PR, not pushed directly.**

### Phase 7A — Wait for /approve

1. Run: `gh pr view <PR_number> --json comments --jq '[.comments[].body] | join("\n")'`
2. Look for a comment containing exactly `/approve` posted by a human
3. If not found → stop and tell the user to post `/approve` on the PR
4. NEVER post `/approve` yourself

### Phase 7B — Finalize issues.md

Fill in:
- **Deferred items** — anything intentionally punted with a target step
- **Tech debt introduced** — shortcuts taken
- **Unresolved at merge** — things left open

### Phase 7C — Update DEFERRED.md

For each deferred item from this step:
```
- **[Step N → Step X]** <description> — <what file to fix>
```

### Phase 7D — Write summary.md

```markdown
# Step N — <Step Name> — Session Summary

## What was built
[Files created/modified with one-line descriptions]

## Key decisions
[Decisions that aren't obvious from reading the code]

## Pitfalls discovered
[Gotchas for future agents]

## Deferred items
[Items punted with target step]

## Env vars added
[New .env vars with purpose]

## Test coverage
[What's covered, what gaps remain]
```

### Phase 7E — Update KANBAN.md (on the feature branch)

```
- [x] **Step N** — <name> — DONE <YYYY-MM-DD> — <one-line summary>
```

### Phase 7F — Update REGRESSION.md

Add smoke tests for this step's features:
```markdown
## Step N smoke tests
- [ ] [endpoint or flow]: [how to verify, expected result]
```

### Phase 7G — Update ARCHITECTURE.md

If this step added endpoints, services, or changed infrastructure — update the relevant section.

### Phase 7H — Commit docs and merge

```bash
git add DOCS/ ARCHITECTURE.md
git commit -m "docs(step-{N}): post-merge finalization"
git push

gh pr merge <PR_number> --squash --delete-branch
git checkout main && git pull origin main
```

### Phase 7I — Report completion

```
Step N complete and merged.

DONE:    [all completed steps]
READY:   [newly unblocked steps]

Run /next to start the next step.
```
