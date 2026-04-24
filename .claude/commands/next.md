# Next — Prioritized work menu

Analyzes all pending work (bugs, deferred items, features, plan steps) and presents a
prioritized numbered menu. The user picks what to work on, then the pipeline runs.

## Instructions

### Step 1 — Gather everything pending

Read these files and collect all actionable items:

1. **`DOCS/BUGS.md`** — all bugs with status OPEN. Note priority (P0/P1/P2/P3).
2. **`DOCS/DEFERRED.md`** — all items not marked COMPLETED or RESOLVED.
3. **`DOCS/BACKLOG.md`** — all feature requests not yet built.
4. **`DOCS/KANBAN.md`** — unchecked items only (look for `- [ ]` lines). Skip completed sections.
5. **`plans/forward.md`** — all steps not yet started.
6. **`git branch -a`** — check for in-progress feature branches not yet merged.

**Do NOT read** `DOCS/pipeline/step-*/summary.md` — completed step info is already in KANBAN.md.

### Step 2 — Prioritize

Sort all items into a single prioritized list using these rules:

| Priority | Type | Rule |
|---|---|---|
| 1 (critical) | P0 bugs | Must fix immediately — before anything else |
| 2 (high) | P1 bugs | Fix in next work session |
| 3 (high) | Deferred 3+ times | Chronic deferrals become blockers — must address |
| 4 (medium) | In-progress branches | Finish what's started before starting new |
| 5 (medium) | Next ready step from plan | Follow the roadmap |
| 6 (medium) | P2 bugs | Fix when convenient |
| 7 (low) | Backlog features | Nice to have |
| 8 (low) | P3 bugs | Minor, fix when nothing else is pending |

### Step 3 — Present the menu

Print a numbered menu with the top items (max 7):

```
Here's what's pending, in priority order:

1. [BUG P1] Short bug description — DOCS/BUGS.md #BUG-3
2. [DEFERRED x3] Item deferred 3 times — now mandatory
3. [IN PROGRESS] feat/some-feature branch — started but not merged
4. [STEP 1] Scaffold & Setup
5. [FEATURE] New feature added by user
6. [BUG P2] Minor bug — DOCS/BUGS.md #BUG-5
7. [STEP 2] Core API — depends on Step 1

Which one do you want to tackle? (number or name)
```

### Step 4 — Run the selected item

Based on user's choice:

- **Bug** → Run `/bug` skill to triage, then fix it (create branch, fix, test, PR)
- **Deferred item** → Create a mini-step for it and run `/pipeline`
- **In-progress branch** → Run `/resume-pr` to pick it up
- **Plan step** → Run `/pipeline "Step N — Name"`
- **Backlog feature** → Run `/pipeline "Step N — Name"`

If the user says "1" or gives a number, map it to the item. If they say a name, match it.

### Step 5 — After completion

After the selected work is done (PR merged), re-run Step 1-3 automatically to show the updated menu. Ask:

```
That's done. Here's what's left:

[updated menu]

Continue with the next one, or done for now?
```
