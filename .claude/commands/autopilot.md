# autopilot — Continuous development loop

Runs unattended, picking the highest-priority item from `/next` and executing it.
Loops until nothing is left, a budget limit is hit, or a failure needs human input.

This is the "set it and forget it" mode. Use `/orchestrate` for more control.

## Usage

```
/autopilot                   ← run until nothing is left
/autopilot --budget 3        ← stop after 3 items completed
/autopilot --hours 2         ← stop after ~2 hours (checks per-loop)
/autopilot --bugs-only       ← only fix bugs, skip features
/autopilot --skip-review     ← autonomous mode (no design gates)
```

## How it works

```
loop:
  1. Run /next logic → get prioritized menu
  2. Pick the #1 item
  3. Based on item type:
     - Bug → create hotfix branch, fix, test, PR
     - Deferred item → inline fix, test, PR
     - Plan step → run /pipeline with gates
  4. After PR created → wait for /approve
  5. After merge → loop back to step 1
  6. Exit conditions:
     - /next returns empty (all done)
     - Budget exhausted
     - Time limit hit
     - Failure requires human input
```

---

## Instructions

### Step 0 — Pre-flight checks

Before entering the loop:
1. Run `git status` — must be clean
2. Run `docker compose ps` — services must be healthy
3. Read `CLAUDE.md` — reload constraints
4. Read `DOCS/KANBAN.md` — understand current state

If anything is off → fix it first or tell the user.

### Step 1 — Priority scan (same as /next logic)

Read and collect all actionable items:
1. `DOCS/BUGS.md` — OPEN bugs
2. `DOCS/DEFERRED.md` — items not COMPLETED/RESOLVED
3. `DOCS/BACKLOG.md` — feature requests
4. `DOCS/KANBAN.md` — unchecked items
5. `plans/forward.md` — unstarted steps
6. `git branch -a` — in-progress branches

Apply priority sort:
```
P0 bugs > P1 bugs > Deferred 3x > In-progress branches > Next ready step > P2 bugs > Backlog > P3 bugs
```

If `--bugs-only`: filter to bugs only.

If no items remain: print "All done. Nothing pending." and exit.

### Step 2 — Execute the top item

Print what's being worked on:
```
[autopilot] Starting item 1/3 (budget: 3):
  [BUG P1] Campaign shows FAILED even when generation succeeds

Creating hotfix branch...
```

Execute based on type:

#### Bugs (P0-P3)
```bash
git checkout main && git pull origin main
git checkout -b fix/bug-{N}-{slug}
```
1. Read the bug entry in DOCS/BUGS.md for root cause hypothesis
2. Read the files likely involved
3. Write a regression test that reproduces the bug (must fail first)
4. Fix the bug (make the test pass)
5. Run full test suite
6. Create PR:
   ```bash
   gh pr create --title "fix(BUG-{N}): {short title}" --body "..."
   ```
7. Mark DOCS/BUGS.md status as `IN PROGRESS` → `PR OPEN`

#### Deferred items
Inline fix on a dedicated branch. Usually small — migration, config change, cleanup.

#### Plan steps
Run the full `/pipeline` in the current gate mode:
- First 3 steps: `guided` mode (gates after requirements + design)
- After that: `autonomous` mode (only /approve gate)

If `--skip-review`: always use autonomous mode.

### Step 3 — Wait for /approve

After PR is created:
```
[autopilot] PR #15 ready for review: fix(BUG-3): Campaign status mapping

Tests: ✓ passing | Build: ✓ clean

→ https://github.com/user/repo/pull/15

Waiting for /approve comment...
To skip this item and move on: reply 'skip'
To stop autopilot: reply 'stop'
```

**Polling strategy:**
1. Check for `/approve` every 60 seconds using:
   ```bash
   gh pr view <PR_number> --json comments --jq '[.comments[].body] | join("\n")'
   ```
2. If `/approve` found → merge and continue
3. If no `/approve` after surfacing → wait (the loop pauses here)

### Step 4 — Post-completion

After merge:
1. Update DOCS/BUGS.md (if bug: mark RESOLVED)
2. Update DOCS/KANBAN.md
3. Decrement budget counter
4. Check exit conditions:
   - Budget hit → print report and exit
   - Time limit hit → print report and exit
   - All done → print report and exit

Print progress:
```
[autopilot] ✓ BUG-3 fixed and merged (1/3 budget used)
[autopilot] Scanning for next item...
```

Loop back to Step 1.

### Step 5 — Failure handling

If any operation fails:
```
[autopilot] ⚠ Implementation failed for Step 2 — Phase 3.

Error: test_create_campaign fails — expected 201, got 422

Options:
  'retry'  → try fixing again with opus
  'skip'   → move to next item, come back to this later
  'stop'   → exit autopilot
```

Never continue silently past a failure. Always surface and ask.

### Step 6 — Exit report

When autopilot exits:

```
=== Autopilot Report ===

Completed: 3 items
  ✓ BUG-3 — Campaign status mapping (PR #15)
  ✓ BUG-5 — Email footer on mobile (PR #16)
  ✓ Step 2 — Core Domain (PR #17)

Still pending: 4 items
  [STEP 3] Dashboard (READY)
  [BUG P2] Swagger button (OPEN)
  ...

To continue: /autopilot
To continue with more control: /orchestrate
```
