# bug — Report a post-merge bug for triage and scheduling

Use this when you find a bug after a step has merged. The agent triages priority,
decides when to fix it, and tracks it in DOCS/BUGS.md.

## Usage

```
/bug "Short description of what broke"
/bug "Free tier limit not enforced" --priority p0
/bug "Swagger lock button missing" --step 4a
```

Arguments:
- First arg: description of the bug (required)
- `--priority p0|p1|p2|p3` (optional — agent will assign if omitted)
- `--step N` (optional — force fix in a specific step)

---

## Instructions

### Step 1 — Understand the bug

**If the bug involves runtime behavior** (not a typo or config issue), run gstack's
`/investigate` skill to systematically trace the root cause before triaging:
```
/investigate
```

Ask the user (or infer from description) for:
1. What did you do? (steps to reproduce)
2. What did you expect to happen?
3. What actually happened? (error message, screenshot, status code)
4. Which step introduced this? (check KANBAN.md and step summaries)

If the description already contains this info — skip asking and proceed.

### Step 2 — Triage priority

| Priority | Criteria | SLA |
|---|---|---|
| P0 | Data loss, security vulnerability, complete feature broken for all users | Fix immediately in hotfix branch |
| P1 | Core user flow broken, workaround exists but painful | Fix in next pipeline step as first task |
| P2 | Feature partially broken, non-critical path | Fix in the step that owns this feature area |
| P3 | Minor UX issue, cosmetic problem, edge case | Schedule to nearest relevant future step |

**P0 rule:** If priority is P0 — do not write to BUGS.md and stop. Instead:
1. Tell the user: "This is P0 — creating hotfix branch now"
2. Run: `git checkout main && git pull origin main && git checkout -b hotfix/step-{N}-{slug}`
3. Fix the bug, write a regression test, verify tests pass
4. Open PR: `gh pr create --title "hotfix: [description]"`

### Step 3 — Determine target step

If `--step` was provided → use that step.

Otherwise:
1. Read `DOCS/KANBAN.md` to see what steps are READY or IN PROGRESS
2. Assign to the earliest step where the fix naturally belongs

For P1: always assign to the very next step that will run.

### Step 4 — Write to DOCS/BUGS.md

Append to `DOCS/BUGS.md` (create if it doesn't exist):

```markdown
---
## BUG-{N}: {short title}
**Priority:** P{0|1|2|3}
**Reported:** {YYYY-MM-DD}
**Target step:** Step {N} — {step name}
**Status:** OPEN

### Description
{what the user reported}

### Steps to reproduce
1. {step}
2. {step}

### Expected
{what should happen}

### Actual
{what actually happens — include error messages verbatim}

### Root cause hypothesis
{agent's best guess at what is broken and where in the code}

### Files likely involved
- {file path}: {why}

### Fix guidance
{concrete direction — specific file, line, and what to change}

### Regression test to add
{describe the test that must be written to prevent this regressing}
```

### Step 5 — Update DEFERRED.md

Add a line to `DOCS/DEFERRED.md` under the target step's section:
```
- **[Bug BUG-{N}]** {short title} — P{priority}, fix in Step {N} before new features
```

### Step 6 — Confirm to user

```
BUG-{N} logged.
Priority: P{X}
Target: Step {N} — {step name}
The pipeline will address this {first thing / as part of / before closing} that step.

Run /next to start the next step (it will pick this up automatically).
```

If P0: print the hotfix branch name and PR link instead.
