# status — Live orchestration dashboard

Shows what the orchestrator / autopilot is currently doing, what's completed,
and what's next. Read-only — does not affect execution.

## Usage

```
/status                  ← full dashboard
/status --brief          ← one-line summary
```

---

## Instructions

### Step 1 — Read the orchestrator status file

Read `DOCS/pipeline/orchestrator-status.md` if it exists.

If it doesn't exist: print "No orchestration in progress. Run /orchestrate to start." and stop.

### Step 2 — Read supporting state

In parallel:
1. Read `DOCS/KANBAN.md` — current step statuses
2. Run `git branch -a | grep feat/step` — active feature branches
3. Run `gh pr list --state open --json number,title,headRefName` — open PRs
4. Read `DOCS/BUGS.md` — any P0/P1 bugs filed since orchestration started

### Step 3 — Print the dashboard

```
=== Orchestration Status ===
Mode: full-auto | Started: 2026-04-25 09:00 | Runtime: 2h 15m

Currently executing:
  Step 3 — Dashboard UI → Phase 3B (implementing Task 2 of 5)

Progress:
  ✓ Step 0 — Scaffold          merged  PR #10   12 min
  ✓ Step 1 — Auth              merged  PR #12   28 min
  ✓ Step 2 — Core API          merged  PR #15   45 min
  ◉ Step 3 — Dashboard UI      Phase 3  PR —    running (18 min so far)
  ○ Step 4 — Workers           blocked  (needs Step 2 ✓, Step 3 ○)
  ○ Step 5 — Paid Features     blocked  (needs Step 4)

Tests after last merge (Step 2):
  Unit: 47 passed | Integration: 12 passed | Regression: 8 passed | E2E: 3 passed

Alerts:
  ⚠ None                       (or: P0 bug filed — orchestrator will pause after Step 3)

Estimated remaining: ~1.5 hours (2 steps)
```

### Step 4 — Check for alerts

Flag any of these:
- P0/P1 bugs in BUGS.md filed after orchestration started
- `.halt` file exists (manual pause requested)
- Plan file hash changed since orchestration started
- Test failures on main after a merge
- Any open PR with failing CI checks

If alerts exist, they appear in the Alerts section.
If `.halt` exists: print "⚠ HALT requested — orchestrator will stop after current phase."
