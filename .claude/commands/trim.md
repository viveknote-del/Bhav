# trim — Archive completed items and keep doc files lean

Run this every 3-5 merged PRs to prevent token bloat.
CLAUDE.md loads on every session — every 100 lines = ~2,500 tokens burned permanently.

## What this does

1. Archives resolved bugs from BUGS.md → BUGS-ARCHIVE.md
2. Archives completed KANBAN tasks → KANBAN-ARCHIVE.md
3. Audits CLAUDE.md size and warns if > 250 lines
4. Audits DEFERRED.md for items that were resolved but not removed
5. Reports token savings from the cleanup

## Instructions

### Step 1 — Audit sizes

Read these files and record their current line counts:
- `CLAUDE.md`
- `DOCS/BUGS.md`
- `DOCS/KANBAN.md`
- `DOCS/DEFERRED.md`

Print a table:
```
File                  Lines    Status
CLAUDE.md             286      ✓ OK (limit: 300)
DOCS/BUGS.md          84       ✓ OK
DOCS/KANBAN.md        112      ⚠ Warn (has completed items to archive)
DOCS/DEFERRED.md      67       ✓ OK
```

### Step 2 — Archive resolved bugs

Read `DOCS/BUGS.md`. Find all bugs with **Status: RESOLVED** or **Status: CLOSED**.

For each resolved bug:
1. Copy its full entry to `DOCS/BUGS-ARCHIVE.md` (create the file if it doesn't exist — add a header first)
2. Remove it from `DOCS/BUGS.md`

After removing, verify `DOCS/BUGS.md` still has its header and any remaining OPEN bugs.

### Step 3 — Archive completed KANBAN tasks

Read `DOCS/KANBAN.md`. Find all checked items: `- [x] **Step N**`.

For each completed step:
1. Copy its line to `DOCS/KANBAN-ARCHIVE.md` (create if it doesn't exist — add a header first)
2. Remove it from `DOCS/KANBAN.md`

Keep the KANBAN header, column headers, and any unchecked items.

### Step 4 — Audit DEFERRED.md

Read `DOCS/DEFERRED.md`. Find any items marked RESOLVED or COMPLETED.
Remove those entries. Log how many were removed.

### Step 5 — Audit CLAUDE.md size

Count lines in `CLAUDE.md`.

If > 300 lines: print this warning and stop — DO NOT auto-edit CLAUDE.md:
```
⚠ CLAUDE.md is {N} lines — over the 300-line limit.

This file loads on every session. Every 100 extra lines ≈ 2,500 tokens wasted.

Common causes:
- Session logs or decisions baked into CLAUDE.md (move to DOCS/DECISIONS.md)
- Resolved pitfalls that no longer apply (remove)
- Architecture details that belong in ARCHITECTURE.md (move there)

Review CLAUDE.md manually and trim to under 250 lines.
Do NOT let agents add content here without removing something else.
```

If ≤ 300 lines: print `✓ CLAUDE.md is {N} lines — within limit.`

### Step 6 — Commit the cleanup

```bash
git add DOCS/
git commit -m "chore: archive resolved bugs and completed kanban tasks — doc hygiene"
```

### Step 7 — Report

Print a before/after table:
```
=== Trim complete ===

File                  Before    After    Lines saved
DOCS/BUGS.md          84        32       52
DOCS/KANBAN.md        112       68       44
DOCS/DEFERRED.md      67        60       7
TOTAL                 263       160      103 (~2,575 tokens/session)

Archived to:
  DOCS/BUGS-ARCHIVE.md     (N resolved bugs)
  DOCS/KANBAN-ARCHIVE.md   (N completed steps)
```
