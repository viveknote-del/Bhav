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
| `guided` (default) | After Phase 1 + Phase 2 + Phase 7A (/approve) | First 3 steps — catches bad requirements early |
| `autonomous` | Only Phase 7A (/approve) | Established projects with clear patterns |
| `full-auto` | Nowhere — only stops on test failure or conflict | Plan already reviewed, trust AI fully |
| `full-control` | After every phase | Debugging the pipeline or learning how it works |

**`full-auto` mode details:**
- The plan MUST be reviewed and approved before entering full-auto
- Phases 0-6 run without any human gates
- Phase 7: skips `/approve` wait — if all tests pass, that IS the approval
- Auto-merges the PR, updates docs, chains to the next step
- Runs parallel agents with worktree isolation for independent tasks
- ONLY stops when: a test suite fails, a merge conflict can't be auto-resolved,
  or opus escalation fails to fix a build error
- This is the "run overnight" mode

**Safety nets in full-auto:**
- Full test pyramid (unit + integration + regression + E2E + security + evals) must pass
- Code review skill still runs and blocks on CRITICAL findings
- Merge conflicts between parallel steps trigger a stop
- Budget limit (`--budget N`) still respected

Switch from `guided` to `autonomous` once you've shipped 3+ steps and trust the patterns.
Switch to `full-auto` once the test suite is comprehensive and you want hands-off execution.

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

### Step 1b — Full-auto pre-flight (full-auto mode only)

If `--mode full-auto`:

1. **Verify the plan was reviewed:**
   ```
   The plan has {N} READY steps. Full-auto mode will:
   - Run all steps autonomously (no human gates)
   - Auto-merge PRs after all tests pass
   - Only stop on failure

   This requires that you've already reviewed plans/forward.md.

   Reply 'go' to start full-auto execution.
   Reply 'review' to see the plan first.
   ```

   This is the ONLY human interaction in full-auto mode.

2. **Check test infrastructure exists:**
   - `services/api/tests/` has at least 1 test file
   - `apps/web/e2e/` has at least 1 spec file
   - `docker compose ps` shows healthy services
   - `DOCS/REGRESSION.md` has at least 3 smoke tests

   If any check fails:
   ```
   ⚠ Full-auto requires comprehensive tests. Missing:
     - No E2E tests in apps/web/e2e/
     - REGRESSION.md has 0 smoke tests

   Fix these first, or use --mode autonomous (stops for /approve).
   ```

3. **Start execution loop:**
   ```
   FOR EACH step in dependency order:
     IF step has parallel peers at same depth:
       Spawn parallel Agent(isolation="worktree") per step
       Each agent runs: /pipeline "Step N" --gate-mode full-auto
       Wait for all agents to complete
       Merge PRs sequentially (first-ready-first-merged)
       Rebase remaining branches if needed
     ELSE:
       Run /pipeline "Step N" --gate-mode full-auto directly
     
     After merge:
       Update KANBAN.md
       Log to fix-log.md
       Verify main is clean: git checkout main && git pull && make sanity
       Continue to next depth level
   ```

---

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


---

## Safety mechanisms (all modes)

### 1. Live status file

The orchestrator writes `DOCS/pipeline/orchestrator-status.md` after every phase transition.
The user can run `/status` at any time to see the dashboard. The file contains:

```markdown
# Orchestrator Status
Mode: full-auto
Started: 2026-04-25T09:00:00Z
Plan hash: a1b2c3 (from plans/forward.md at start)

## Current
Step 3 — Dashboard UI | Phase 3B | Task 2/5 | running since 09:45

## Completed
| Step | PR | Duration | Tests |
|---|---|---|---|
| Step 0 | #10 | 12m | 8/8 passed |
| Step 1 | #12 | 28m | 24/24 passed |
| Step 2 | #15 | 45m | 47/47 passed |

## Remaining
| Step | Status | Depends on |
|---|---|---|
| Step 4 | blocked | Step 2 ✓, Step 3 ○ |
| Step 5 | blocked | Step 4 |

## Alerts
None
```

**Write this file at every phase transition.** It's the user's window into the running orchestration.

### 2. Halt file checking

Between every phase and between every step, check:

```bash
if [ -f .halt ]; then
  echo "Halt signal detected."
  # Read reason
  cat .halt
  # Write checkpoint
  # Report and stop
fi
```

The user creates `.halt` via the `/halt` command. The orchestrator finishes its current phase,
writes checkpoint, and stops cleanly. No work is lost.

### 3. Plan change detection

At orchestration start, hash the plan file:
```bash
PLAN_HASH=$(md5 -q plans/forward.md)
```

Between every step (after merge, before starting next step), re-hash:
```bash
NEW_HASH=$(md5 -q plans/forward.md)
if [ "$NEW_HASH" != "$PLAN_HASH" ]; then
  echo "⚠ Plan changed since orchestration started."
  echo "Re-reading plan and rebuilding dependency graph..."
  # Re-parse plan, re-check dependencies
  # Some steps may have been added, removed, or reordered
  # Present the new plan to the user:
  echo "Plan changed. New execution order:"
  # ... show diff
  echo "Reply 'continue' to accept, 'halt' to stop and review."
fi
```

This catches:
- New steps added via `/feature`
- Steps removed or reordered
- Dependency changes
- Any manual edits to `plans/forward.md`

### 4. Priority interrupt (P0/P1 bug check)

Between every step, check `DOCS/BUGS.md` for new P0/P1 bugs:

```bash
# Check for P0 bugs filed since orchestration started
grep -c "Priority.*P0.*Status.*OPEN" DOCS/BUGS.md
```

If a P0 is found:
```
⚠ P0 bug detected: BUG-7 — payment endpoint returns 500

P0 bugs take priority over all planned work.
Pausing orchestration to fix BUG-7 first.

Creating hotfix branch: hotfix/bug-7-payment-500
```

The orchestrator:
1. Pauses the current plan
2. Fixes the P0 bug (hotfix branch → PR → merge)
3. Resumes the plan from where it paused

For P1 bugs: log a warning but continue. The P1 will be picked up in the next step
if it targets that step (pipeline Phase 0 reads BUGS.md).

### 5. Post-merge verification on main

After EVERY step merges, run the full test suite on main:

```bash
git checkout main && git pull origin main

# Full verification on main
pytest services/api/tests/ -v --tb=short
cd apps/web && pnpm tsc --noEmit && pnpm build && pnpm test
./scripts/sanity-check.sh
```

If main is broken after the merge:

```
⚠ Main is broken after merging Step 2 (PR #15).

Failing: test_campaign_create — expected 201, got 500

Options:
1. Attempt auto-fix: spawn opus agent to diagnose and fix on main
2. Revert the merge: git revert <merge-sha> && git push
3. Halt: stop orchestration, surface to user

Attempting auto-fix first...
```

Auto-fix flow:
1. Create a `fix/post-merge-step-{N}` branch from main
2. Spawn opus agent to diagnose and fix
3. Run tests again
4. If green → merge the fix, continue orchestration
5. If still broken → revert the original merge, halt, surface to user

**NEVER continue to the next step if main is broken.** Everything depends on a green main.

### 6. Rollback capability

If a step needs to be rolled back:

```bash
# Find the merge commit
MERGE_SHA=$(git log --oneline -1 --merges | cut -d' ' -f1)

# Revert it
git revert $MERGE_SHA --no-edit
git push origin main

# Update KANBAN.md — mark step as REVERTED
# Update DEFERRED.md — note what needs re-implementation
```

Rollback triggers:
- Post-merge tests fail AND auto-fix fails
- User runs `/halt --rollback <step>`
- A subsequent step reveals the prior step's implementation was fundamentally wrong


### Step 5 — Final report

When orchestration ends (all steps done, budget hit, or user stopped):

```
=== Orchestration Report ===

Completed: Step 0, Step 1, Step 2
PRs merged: #10, #12, #15
Steps remaining: Step 3 (READY), Step 4 (BLOCKED by 3)

Next time: /orchestrate to continue from Step 3
```
