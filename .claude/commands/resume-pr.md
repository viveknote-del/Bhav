# resume-pr — Resume a pipeline session from a stalled PR

Use this when a pipeline session ended before Phase 7 completed (PR open, post-merge docs not written).

## Usage

```
/resume-pr <PR_number>
```

Example: `/resume-pr 12`

---

## Instructions

### Step 1 — Load context

1. Run `gh pr view <PR_number>` to get PR title, status, branch, and description
2. Derive the step name from the PR title (e.g. "feat(step-3): ..." → Step 3)
3. Read `DOCS/KANBAN.md` to confirm the step's current status
4. Read `DOCS/pipeline/step-{N}/summary.md` if it exists — skip if not yet written
5. Read `DOCS/pipeline/step-{N}/issues.md` if it exists
6. Read `plans/forward.md` section for this step to understand what was built
7. Read `DOCS/BUGS.md` — find any OPEN P0/P1 bugs targeting this step; must be resolved before merge
8. Read `DOCS/BACKLOG.md` if it exists — find any SCHEDULED features targeting this step

### Step 2 — Check PR state

Run these in parallel:

```bash
gh pr view <PR_number> --json state,mergeable,reviewDecision,statusCheckRollup
gh pr checks <PR_number>
```

**If PR is already merged:**
→ Jump to Step 4 (post-merge docs)

**If PR has review comments:**

Run: `gh pr view <PR_number> --comments --json comments`

For each comment thread:
1. Check if the comment was already addressed: look for a reply saying "fixed", "done", "addressed"
2. If already addressed AND the fix was pushed → mark as resolved, skip it
3. If NOT yet addressed → read the code, make the fix, re-run affected tests

**Never re-fix something that already has a resolution reply and a subsequent commit.**

After addressing all unresolved comments, reply to each with what was done:
```
Fixed in <commit-sha>: <one sentence describing the fix>
```

Then commit: `git commit -m "fix(step-N): address PR review comments"`
Push: `git push origin <branch>`

**If CI is failing:**
→ Read the failing check output via `gh run view <run_id> --log-failed`
→ Fix the failure, commit, push

**If PR is open and clean (no comments, CI green):**
→ Proceed to Step 4 (write docs first, merge after).

### Step 3 — Verify human approval before any merge

**Before merging — verify human approval:**
1. Run: `gh pr view <PR_number> --json comments --jq '[.comments[].body] | join("\n")'`
2. Look for a comment containing exactly `/approve` posted by a human
3. If no `/approve` found → print "Waiting for human /approve on PR #<N>. Do not merge yet." and STOP.
4. NEVER post `/approve` yourself. NEVER merge without it.
5. If `/approve` is found → proceed to Step 4.

**CRITICAL: Do NOT merge yet.** Write all post-merge docs on the feature branch first (Step 4), then merge in Step 5 — so docs go through the PR and land on main together.

### Step 4 — Post-merge docs (write on the feature branch, before merging)

#### 4a. Check testing.md exists

Read `DOCS/pipeline/step-{N}/testing.md`. If it doesn't exist, write it now following Phase 6C format in pipeline.md — cover every endpoint/migration/UI change with copy-pasteable commands and expected outputs.

#### 4b. Finalize issues.md

Read `DOCS/pipeline/step-{N}/issues.md`. Fill in any empty sections:
- **Deferred items** — anything intentionally punted with a target step
- **Tech debt introduced** — shortcuts taken with known cleanup path
- **Unresolved at merge** — things left open

#### 4c. Update DEFERRED.md

Read `DOCS/DEFERRED.md`. For each deferred item from this step:
- Add it under the correct "Due in Step X" section
- Format: `- **[Step N]** <description> — <where to fix>`

#### 4d. Update ARCHITECTURE.md

If this step changed the architecture, update the relevant section.

#### 4e. Write summary.md

Write `DOCS/pipeline/step-{N}/summary.md`:

```markdown
# Step N — <Step Name> — Session Summary

## What was built
[Bulleted list of files created/modified with one-line descriptions]

## Key decisions
[Decisions that aren't obvious from reading the code — why X over Y]

## Pitfalls discovered
[Gotchas that future agents should know]

## Deferred items
[Items punted with target step]

## Env vars added
[New .env vars introduced, with purpose]

## Test coverage
[What's covered, any gaps]
```

#### 4f. Update KANBAN.md (on the feature branch)

Mark the step DONE with today's date:
```
- [x] **Step N** — <name> — DONE <YYYY-MM-DD> — <one-line summary>
```

Update the header: `> Last updated: <date> | **Step N DONE — Step X READY**`

#### 4g. Commit all docs and push

```bash
git add DOCS/ ARCHITECTURE.md
git commit -m "docs(step-N): post-merge finalization — summary, deferred, kanban"
git push
```

### Step 5 — Merge the PR (after docs are on the branch)

```bash
gh pr merge <PR_number> --squash --delete-branch
git checkout main && git pull origin main
```

Confirm: `git log --oneline -3`

### Step 6 — Report completion

```
Step N post-merge finalization complete.

DONE:    [list all done steps]
READY:   [list all newly unblocked steps]

Run /next to start the next step.
```
