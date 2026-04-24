# orchestrate — Multi-step development orchestrator

Reads the plan, resolves dependencies, and runs steps sequentially or in parallel.
This is the "autopilot" for your entire product — it chains `/pipeline` runs
across steps, manages human gates, and tracks progress.

## Usage

```
/orchestrate                         ← run all READY steps, guided mode (stops for design review)
/orchestrate --mode autonomous       ← only stop at PR /approve (trust AI design)
/orchestrate --mode full-control     ← stop after every phase for review
/orchestrate --steps 1,2,3           ← run specific steps only
/orchestrate --parallel              ← identify which steps can run in parallel
/orchestrate --budget 5              ← max 5 steps then stop (cost control)
/orchestrate --dry-run               ← show the execution plan without running anything
```

## Gate modes

| Mode | Stops at | Best for |
|---|---|---|
| `guided` (default) | After Phase 1 (requirements) + Phase 2 (design) + Phase 7A (/approve) | First 3 steps of any project — catches bad requirements early |
| `autonomous` | Only Phase 7A (/approve) | Established projects with clear patterns |
| `full-control` | After every phase | Debugging the pipeline or learning how it works |

Switch from `guided` to `autonomous` once you've shipped 3+ steps and trust the patterns.

---

## Instructions

### Step 0 — Parse the plan and build the dependency graph

Read `plans/forward.md`. For each step, extract:
- Step number
- Step name
- `Depends on:` value (which steps must be DONE first)
- Bullet points (scope)

Read `DOCS/KANBAN.md`. For each step, determine its status:
- `DONE` — completed and merged
- `IN PROGRESS` — has a branch or open PR
- `READY` — all dependencies are DONE, not yet started
- `BLOCKED` — has unmet dependencies

Build the execution order:

```
Step 0 — Scaffold             [DONE]
Step 1 — Auth                 [READY]  (depends: 0 ✓)
Step 2 — Core Domain          [BLOCKED] (depends: 1 ✗)
Step 3 — Dashboard            [BLOCKED] (depends: 1 ✗)
Step 4 — Workers              [BLOCKED] (depends: 2 ✗)
```

### Step 1 — Identify parallel opportunities

Find steps at the same dependency depth that are both READY:
```
If Step 2 and Step 3 both depend only on Step 1,
and Step 1 is DONE, then Steps 2 and 3 can run in parallel.
```

Print the execution plan:

```
=== Orchestration Plan ===
Mode: guided
Budget: unlimited

Phase 1 (sequential):
  → Step 1 — Auth [READY]

Phase 2 (parallel — 2 steps):
  → Step 2 — Core Domain [after Step 1]
  → Step 3 — Dashboard   [after Step 1]

Phase 3 (sequential):
  → Step 4 — Workers [after Step 2]

Estimated: 4 steps, ~2-4 hours autonomous + review time
```

If `--dry-run`: print the plan and stop.

If `--parallel`: print which steps can run simultaneously and suggest the user
open multiple Conductor workspaces (one per parallel step). Print instructions:

```
Steps 2 and 3 are independent and can run in parallel.

To run them simultaneously:
1. Create a new Conductor workspace for each step
2. In workspace 1: /pipeline "Step 2 — Core Domain"
3. In workspace 2: /pipeline "Step 3 — Dashboard"

Both will create separate PRs. Merge them in sequence (Step 2 first, then Step 3).
After both are merged, Step 4 becomes READY.
```

### Step 2 — Execute the first READY step

For the first READY step (or the one specified by `--steps`):

#### Phase gate: requirements (guided + full-control modes)

Run `/pipeline` Phase 0 and Phase 1 only (context load + requirements):
1. Load context (Phase 0)
2. Generate requirements.md (Phase 1)
3. **STOP** and surface the requirements to the user:

```
Requirements for Step 1 — Auth are ready.

Key acceptance criteria:
  - Users can sign up with email/password
  - JWT flows through to API
  - Profile endpoint returns user data

📄 Full requirements: DOCS/pipeline/step-1/requirements.md

Review and reply:
  'ok'        → proceed to design
  'change X'  → I'll update the requirements
  'skip gate' → switch to autonomous mode for this step
```

Wait for user response. If `autonomous` mode: skip this gate.

#### Phase gate: design (guided + full-control modes)

Run Phase 2 (design):
1. Generate design.md (Phase 2)
2. **STOP** and surface the design:

```
Design for Step 1 — Auth is ready.

Architecture:
  - New files: auth.py, routers/users.py, services/user_service.py
  - Migration: 0002_profiles.sql
  - Endpoints: POST /v1/auth/signup, POST /v1/auth/login, GET /v1/users/me
  - Frontend: login page, signup page, useAuth hook

📄 Full design: DOCS/pipeline/step-1/design.md

Review and reply:
  'ok'        → start implementation (Phase 3 — this takes the longest)
  'change X'  → I'll update the design
  'skip gate' → switch to autonomous mode for this step
```

Wait for user response. This is the most valuable gate — wrong design wastes hours.

#### Implementation through PR (Phase 3-6)

Run Phases 3-6 autonomously:
1. Phase 3: implement (spawn haiku agents, escalate to opus on failure)
2. Phase 4: create PR
3. Phase 5: self-review and fix
4. Phase 6: verify all tests

**STOP** when PR is ready:
```
PR #12 ready for review: feat(step-1): Authentication & User Management

Tests: ✓ 24 passing
Build: ✓ clean
Lint:  ✓ clean

→ https://github.com/user/repo/pull/12

Post /approve as a comment on the PR when you're satisfied, then I'll merge
and continue to the next step.
```

#### Phase gate: merge (all modes)

1. Wait for `/approve` comment on the PR
2. Run Phase 7: merge + docs
3. Update `DOCS/KANBAN.md`
4. Print completion

### Step 3 — Chain to next step

After the step merges:

1. Re-read `DOCS/KANBAN.md` and `plans/forward.md`
2. Determine which steps are now READY (dependencies just changed)
3. Check budget: if `--budget N` was set, decrement and stop if 0

If more steps are READY:
```
Step 1 merged. Step 2 and Step 3 are now READY.

[if parallel is possible]
Steps 2 and 3 are independent — want to run them in parallel?
  'parallel'  → I'll give you Conductor workspace instructions
  'next'      → I'll run Step 2 first (sequential)
  'done'      → Stop orchestration for now

[if only one step is ready]
Starting Step 2 — Core Domain...
```

Continue the loop until:
- No more READY steps
- Budget limit reached
- User says 'done'

### Step 4 — Handle failures

If any phase fails:

```
⚠ Step 2 — Phase 3 failed after opus escalation.

Error: TypeError in campaign_service.py — repo.create() returns dict, not CampaignResponse

Options:
  'fix'       → I'll attempt another fix with full opus context
  'skip'      → Defer this task, continue with other parts of the step
  'abort'     → Stop this step, move to next READY step
  'stop'      → Stop orchestration entirely
```

Never silently continue past a failure. Always surface and ask.

### Step 5 — Final report

When orchestration ends (all steps done, budget hit, or user stopped):

```
=== Orchestration Report ===

Completed: Step 0, Step 1, Step 2
PRs merged: #10, #12, #15
Steps remaining: Step 3 (READY), Step 4 (BLOCKED by 3)

Next time: /orchestrate to continue from Step 3
```
