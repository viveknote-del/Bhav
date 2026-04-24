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


## Gate modes (set by /orchestrate or passed as argument)

When invoked by `/orchestrate`, the pipeline receives a gate mode. When run
standalone, the default is `guided`.

| Mode | Gates (where the pipeline stops for human input) |
|---|---|
| `guided` (default) | After Phase 1, after Phase 2, after Phase 6 (wait for /approve) |
| `autonomous` | Only after Phase 6 (wait for /approve) |
| `full-control` | After every phase |

### How gates work

At a gate, the pipeline:
1. Writes checkpoint.md with the current phase status
2. Prints a summary of what was produced (requirements, design, or PR)
3. Asks the user: `'ok'` / `'change X'` / `'skip gate'`
4. If `'ok'` → continue to next phase
5. If `'change X'` → apply the change, re-run the phase, re-gate
6. If `'skip gate'` → switch to autonomous mode for the rest of this step

When running inside `/autopilot`, gates that would block are handled by
the autopilot's polling loop — the pipeline surfaces the gate, autopilot
waits for user response.

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


### Phase 1 gate (guided + full-control modes)

If gate mode is `guided` or `full-control`:

Print a summary of the requirements to the user:
```
Requirements for Step {N} ready.

Key acceptance criteria:
  [top 3-5 criteria from requirements.md]

Full doc: DOCS/pipeline/step-{N}/requirements.md

Reply 'ok' to proceed to design, 'change X' to adjust, or 'skip gate' for autonomous.
```

Wait for user response. If `autonomous` mode: skip this gate.


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


### Phase 2 gate (guided + full-control modes)

If gate mode is `guided` or `full-control`:

Print a summary of the design:
```
Design for Step {N} ready.

Architecture changes:
  [list new files and endpoints]

Key decisions:
  [1-3 design decisions from design.md]

Full doc: DOCS/pipeline/step-{N}/design.md

Reply 'ok' to start implementation, 'change X' to adjust, or 'skip gate' for autonomous.

⚠ This is the most valuable gate — wrong design wastes hours of implementation.
```

Wait for user response. If `autonomous` mode: skip this gate.


---

## Phase 3 — Implementation (parallel agents with worktree isolation)

**Model: haiku by default. Escalate to opus on any failure.**

### Phase 3A — Decompose into parallel tasks

Read `DOCS/pipeline/step-{N}/design.md`. Break it into independent implementation tasks.

Rules for task decomposition:
- Each task touches a distinct set of files (no overlap → no merge conflicts)
- Backend tasks: group by layer (migration, repository, service, router, tests)
- Frontend tasks: group by page or component (one page = one task)
- Each task must be self-contained: a task that writes a router also writes its tests

Write the task list to `DOCS/pipeline/step-{N}/journeys.md`:

```markdown
# Step N — Implementation Tasks

## Task 1: Database migration + repository
Files: packages/database/migrations/0002_*.sql, services/api/repositories/item_repo.py
Tests: services/api/tests/test_item_repo.py
Agent: haiku

## Task 2: Service layer + business logic
Files: services/api/services/item_service.py, services/api/models/item.py
Tests: services/api/tests/test_item_service.py
Depends on: Task 1 (needs repo)
Agent: haiku

## Task 3: Router endpoints
Files: services/api/routers/items.py
Tests: services/api/tests/test_items_router.py
Depends on: Task 2 (needs service)
Agent: haiku

## Task 4: Frontend list + detail pages
Files: apps/web/src/app/(app)/items/page.tsx, apps/web/src/hooks/useItems.ts
Tests: apps/web/src/__tests__/items.test.tsx
Depends on: none (can mock API)
Agent: haiku

## Task 5: E2E tests
Files: apps/web/e2e/items.spec.ts
Depends on: Tasks 3 + 4 (needs both API and UI)
Agent: haiku
```

### Phase 3B — Execute tasks (parallel where possible, sequential where dependent)

Group tasks by dependency depth and run each depth level in parallel:

```
Depth 0 (no deps — run in parallel):
  Agent(model="haiku", isolation="worktree") → Task 1: migration + repo
  Agent(model="haiku", isolation="worktree") → Task 4: frontend pages

Depth 1 (depends on depth 0 — run in parallel after depth 0 completes):
  Agent(model="haiku", isolation="worktree") → Task 2: service layer

Depth 2:
  Agent(model="haiku", isolation="worktree") → Task 3: router endpoints

Depth 3:
  Agent(model="haiku", isolation="worktree") → Task 5: E2E tests
```

**Concrete Agent tool call pattern for each task:**

```
Agent(
  subagent_type: "general-purpose",
  model: "haiku",
  isolation: "worktree",
  description: "Implement Task {T}: {task name}",
  prompt: "
    You are implementing Task {T} of Step {N} for {{PROJECT_DISPLAY_NAME}}.
    
    CONTEXT — read these files first:
    - CLAUDE.md (project conventions — CRITICAL)
    - DOCS/pipeline/step-{N}/design.md (what to build)
    - DOCS/pipeline/step-{N}/journeys.md (task breakdown + file assignments)
    - ARCHITECTURE.md (current system shape)
    
    YOUR TASK:
    {paste the specific task description from journeys.md}
    
    FILES YOU OWN (only touch these):
    {list the exact files from the task breakdown}
    
    CONVENTIONS:
    - FastAPI: Router → Service → Repository. Never skip layers.
    - All AI calls through providers/llm.py
    - All API routes under /v1/ prefix
    - Pydantic models: separate request vs response types
    - Tests: AAA pattern (Arrange/Act/Assert)
    - See DOCS/CODE-STANDARDS.md for naming + patterns
    
    AFTER IMPLEMENTING:
    1. Write unit tests for every public function
    2. Run: pytest services/api/tests/ -v (or cd apps/web && pnpm test)
    3. Run: cd apps/web && pnpm tsc --noEmit (if touching frontend)
    4. If tests pass → commit with: git commit -m 'feat(step-{N}): {task description}'
    5. If tests fail → fix and re-run (one retry)
    6. If still failing → report the failure, do NOT leave broken code
    
    WRITE BLOCKERS to DOCS/pipeline/step-{N}/issues.md if any.
  "
)
```

**After each depth level completes:**
1. Merge all worktree branches into the feature branch:
   ```bash
   # Worktree agents return their branch names
   git merge <worktree-branch-1> --no-edit
   git merge <worktree-branch-2> --no-edit
   ```
2. Run integration tests to catch cross-task conflicts
3. If conflicts or failures → spawn opus agent to resolve

**Escalation rule** (same as before):
- If any haiku agent fails tests after 1 retry → spawn opus to diagnose and fix
- If opus can't fix it → STOP and surface to user
- Escalation is expected ~20% of the time — it's a cost optimization, not a failure

### Phase 3C — Integration verification

After all tasks merge into the feature branch:

```bash
# Full backend test suite
pytest services/api/tests/ -v --tb=short

# Frontend build + tests
cd apps/web && pnpm tsc --noEmit && pnpm build && pnpm test

# Prompt evals (if any prompt files changed)
cd services/api && python -m evals.runner

# Docker sanity
docker compose up -d && ./scripts/sanity-check.sh
```

If anything fails → spawn opus agent to diagnose and fix:
```
Agent(
  model: "opus",
  prompt: "
    Integration tests failed after merging parallel implementation tasks.
    
    Error output: {paste the failure}
    
    Read DOCS/pipeline/step-{N}/design.md for what was intended.
    Read the test file and the implementation.
    Fix the issue. Run tests again. Commit the fix.
  "
)
```

Log every fix to `DOCS/pipeline/step-{N}/fix-log.md`:
```
{timestamp} {commit-sha}: {what was fixed}
```

Update `checkpoint.md`:
```
Phase 3 complete: all tasks implemented, integration tests passing
```

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

## Phase 5 — Push and pre-verification

Push the implementation branch and do a quick pre-check before full verification:
```bash
git push -u origin feat/step-{N}-{slug}

# Quick sanity — these should already pass from Phase 3C
pytest services/api/tests/ -v --tb=line
cd apps/web && pnpm tsc --noEmit
```

If anything fails here that passed in Phase 3C → investigate what changed between merge and push.

---

## Phase 6 — Verification (full test pyramid)

Run ALL test layers in sequence. Each layer must pass before moving to the next.
If any layer fails → fix, commit, push, re-run that layer. Log every fix.

### Phase 6A — Unit tests

```bash
# Backend unit tests
cd services/api && pytest tests/ -v --tb=short

# Frontend unit tests
cd apps/web && pnpm test
```

**Coverage check** — invoke the `test-coverage` gstack skill:
```
/test-coverage
```
Target: 80% line coverage minimum. If below threshold, write missing tests before proceeding.

### Phase 6B — Integration tests

```bash
# Backend integration tests (hit real DB — docker compose must be running)
cd services/api && pytest tests/ -v -k "integration" --tb=short

# Frontend build (catches import/type errors across modules)
cd apps/web && pnpm tsc --noEmit && pnpm build
```

### Phase 6C — Regression tests

Read `DOCS/REGRESSION.md`. Run every smoke test defined there — these catch
cross-step breakage from prior features.

```bash
# Example regression checks (project-specific — read REGRESSION.md for actual list)
# API endpoints from prior steps still respond correctly
# Frontend pages from prior steps still load
# Workers from prior steps still enqueue and complete
```

Log results in `DOCS/pipeline/step-{N}/testing.md` under "Regression results".

### Phase 6D — Smoke tests

```bash
# Start all services fresh
docker compose down && docker compose up -d
sleep 5

# Run health checks
./scripts/sanity-check.sh
```

If any service fails to start or health check fails → fix before continuing.

### Phase 6E — E2E browser tests (gstack skill)

Invoke the `e2e` gstack skill to generate and run Playwright browser tests:

```
/e2e
```

This skill:
1. Reads the user journeys from `DOCS/pipeline/step-{N}/journeys.md`
2. Generates Playwright test specs for each journey
3. Runs them against the local dev server
4. Captures screenshots on failure
5. Reports pass/fail with artifacts

If the `/e2e` skill is not available, fall back to running existing Playwright tests:
```bash
cd apps/web && npx playwright install --with-deps chromium
cd apps/web && npx playwright test --reporter=list
```

If no E2E tests exist yet, generate them from journeys.md:

```
Agent(
  subagent_type: "e2e-runner",
  prompt: "
    Read DOCS/pipeline/step-{N}/journeys.md for the user flows.
    Read apps/web/e2e/ for existing test patterns.
    
    Generate Playwright E2E tests for every new user journey in this step.
    
    Each test should:
    - Navigate to the page
    - Perform the user action
    - Assert the expected outcome is visible
    - Use page.waitForSelector() or expect(locator).toBeVisible() — no sleep()
    
    Save to apps/web/e2e/step-{N}-*.spec.ts
    Run: npx playwright test apps/web/e2e/step-{N}-*.spec.ts
    Fix any failures.
  "
)
```

### Phase 6F — Security scan (gstack skill)

Invoke the `security-review` gstack skill on the diff:

```
/security-review
```

This scans for:
- Hardcoded secrets
- SQL injection vectors
- XSS in frontend
- Missing auth guards on endpoints
- OWASP Top 10 issues

If CRITICAL findings → fix immediately. HIGH → fix if < 30 min. MEDIUM/LOW → log to issues.md.

### Phase 6G — Code review (gstack skill)

Invoke the `review` gstack skill (this replaces the old Phase 5):

```
/review
```

This runs a multi-agent code review: code quality, patterns, security, and type safety.
Address CRITICAL and HIGH findings. Log MEDIUM/LOW to issues.md.

### Phase 6H — Prompt evals (if prompts changed)

If any files in `services/api/prompts/` were modified:
```bash
cd services/api && python -m evals.runner --ci
```
Must pass 100%. If any eval fails → fix the prompt, re-run.

### Phase 6I — Write testing.md

Write `DOCS/pipeline/step-{N}/testing.md` — comprehensive verification record:

```markdown
# Step N — Testing Guide

## Test pyramid results

| Layer | Tests | Passed | Failed | Coverage |
|---|---|---|---|---|
| Unit (backend) | 24 | 24 | 0 | 87% |
| Unit (frontend) | 12 | 12 | 0 | 82% |
| Integration | 8 | 8 | 0 | — |
| Regression | 15 | 15 | 0 | — |
| E2E (browser) | 5 | 5 | 0 | — |
| Prompt evals | 4 | 4 | 0 | — |
| Security scan | — | clean | — | — |

## How to run locally

### Setup
[prerequisites — docker compose up, env vars]

### Backend tests
pytest services/api/tests/ -v
Expected: {N} passed in Xs

### Frontend tests
cd apps/web && pnpm test
Expected: {N} passed

### E2E tests
cd apps/web && npx playwright test
Expected: {N} passed

### Smoke tests
./scripts/sanity-check.sh
Expected: all checks passed

## What is NOT tested
[honest list of gaps — what could still break]
```

Update `checkpoint.md`:
```
Phase 6 complete: all test layers passing, testing.md written
  Unit: {N} passed, {coverage}%
  Integration: {N} passed
  Regression: {N} passed
  E2E: {N} passed
  Security: clean
  Prompt evals: {N}/{N} passed
```

---

## Phase 7 — Post-merge docs

**CRITICAL: Write all docs on the feature branch BEFORE merging. Docs must land on main through the PR, not pushed directly.**

### Phase 7A — Merge gate

**Gate behavior depends on mode:**

**`full-auto` mode** (set by `/orchestrate --full-auto`):
- Skip the `/approve` wait entirely
- All tests passed in Phase 6 → that IS the approval
- Proceed directly to merge
- ONLY use this mode when the plan was explicitly approved by the user beforehand

**`autonomous` / `guided` mode** (default):
1. Run: `gh pr view <PR_number> --json comments --jq '[.comments[].body] | join("\n")'`
2. Look for a comment containing exactly `/approve` posted by a human
3. If not found → stop and tell the user to post `/approve` on the PR
4. NEVER post `/approve` yourself

**`full-control` mode**:
- Same as autonomous, plus print a detailed summary of everything that was built and tested

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
