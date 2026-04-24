# Orchestration Guide

How to automate the development process — from single steps to full autopilot.

---

## Automation levels

Choose based on how much you trust the patterns and how involved you want to be:

| Level | Command | You do | Agent does | Best for |
|---|---|---|---|---|
| Manual | `/pipeline "Step N"` | Trigger each step | One full SDLC cycle | Learning the pipeline |
| Guided | `/orchestrate` | Review requirements + design + /approve PR | Everything else | First 3 steps of a new project |
| Autonomous | `/orchestrate --mode autonomous` | /approve PRs | Requirements, design, impl, test | Established patterns |
| Autopilot | `/autopilot` | /approve PRs | Also picks what to work on | Burndown mode (bugs + backlog) |

### Progression recommendation

```
New project:        manual → guided → autonomous
Weeks 1-2:          guided (review every design)
Weeks 3+:           autonomous (trust the patterns)
Bug burndown:       autopilot --bugs-only
Hackathon / sprint: autopilot --skip-review
```

---

## How the pipeline phases map to human gates

```
                    ┌─── HUMAN GATE (guided mode)
                    │    "Review requirements. Reply 'ok'."
                    ▼
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7
context   req'mts    design    implement  create PR  review    verify    merge
                       │                                                   │
                       └── HUMAN GATE (guided mode)                        └── HUMAN GATE (all modes)
                           "Review design. Reply 'ok'."                        "Post /approve on PR"
```

In `autonomous` mode, only the final gate exists.
In `full-control` mode, there's a gate after EVERY phase.

---

## Parallel execution with Conductor

When two steps are independent (no dependency between them), run them in
separate Conductor workspaces simultaneously.

### How to identify parallel opportunities

```
plans/forward.md:
  Step 2 — Core API       (depends: Step 1)
  Step 3 — Dashboard UI   (depends: Step 1)
  Step 4 — Workers        (depends: Step 2)
```

Steps 2 and 3 both depend on Step 1 only. Once Step 1 is DONE, they can
run in parallel.

Step 4 depends on Step 2, so it must wait.

### Execution pattern

```
Time →
Workspace 1:  [Step 1]──────merge──[Step 2]──────merge──[Step 4]
Workspace 2:                       [Step 3]──────merge
                                   ↑ starts same time
```

### Setup instructions

1. `/orchestrate --parallel` shows which steps can run simultaneously
2. Create a Conductor workspace per parallel step
3. In each workspace:
   ```
   /pipeline "Step N — Name"
   ```
4. Each creates its own feature branch and PR
5. **Merge order matters**: merge whichever PR is ready first, then rebase the other

### Merge conflicts

Parallel steps touching different files: no conflicts, merge in any order.
Parallel steps touching shared files (CLAUDE.md, package.json): merge one
first, then rebase the other before merging.

```bash
# After merging Step 2's PR, rebase Step 3's branch:
git checkout feat/step-3-dashboard
git fetch origin
git rebase origin/main
# Resolve any conflicts, then push
git push --force-with-lease
```

---

## Dependency graph resolution

The orchestrator parses `Depends on:` from `plans/forward.md` to build an
execution DAG. Rules:

1. A step is READY when ALL its dependencies are DONE
2. A step is BLOCKED when ANY dependency is not DONE
3. Steps with no dependencies are READY immediately (Step 0)
4. Circular dependencies are an error — the orchestrator stops and asks

### Example DAG

```
Step 0 (scaffold)
  └── Step 1 (auth)
       ├── Step 2 (core API)
       │    └── Step 4 (workers)
       │         └── Step 5 (paid features)
       └── Step 3 (dashboard)
            └── Step 5 (paid features)
```

Execution:
```
Sequential: 0 → 1 → 2 → 3 → 4 → 5
Parallel:   0 → 1 → [2, 3] → 4 → 5
```

Step 5 has two parents (Step 4 AND Step 3) — it waits for BOTH.

---

## Cost control

### Budget limits

```
/orchestrate --budget 3        ← stop after 3 steps
/autopilot --budget 5          ← stop after 5 items
```

### Estimated costs per step (Claude Code usage)

| Step complexity | Phases 0-2 | Phase 3 | Phases 4-7 | Total |
|---|---|---|---|---|
| Simple (1-2 files) | ~$0.50 | ~$1-2 | ~$0.50 | ~$2-3 |
| Medium (3-6 files) | ~$1.00 | ~$3-5 | ~$1.00 | ~$5-7 |
| Complex (7+ files) | ~$2.00 | ~$5-10 | ~$2.00 | ~$9-14 |

The escalation rule (haiku → opus) is the main cost lever in Phase 3.
A step where haiku handles everything: ~$1-3.
A step where opus fires on every task: ~$8-15.

### Monitoring spend

Token usage is logged by `providers/llm.py` on every LLM call. Check your
Claude Code usage dashboard or grep logs:
```bash
grep "llm.usage" logs/api.log | python3 -c "
import sys, json
total = sum(json.loads(l)['input_tokens'] + json.loads(l)['output_tokens'] for l in sys.stdin)
print(f'Total tokens: {total:,}')
"
```

---

## Checkpoint and recovery

Every phase writes to `DOCS/pipeline/step-{N}/checkpoint.md`:

```
Phase 0 complete: context loaded, branch created
Phase 1 complete: requirements.md written
Phase 2 complete: design.md written
Phase 3 complete: all tasks implemented, tests passing
Phase 4 complete: PR #12 opened
Phase 5 complete: review findings addressed
Phase 6 complete: all tests passing, testing.md written
Phase 7 complete: merged, docs finalized
```

If a session dies mid-step:
1. Open a new session in the same workspace
2. Run `/resume-pr <PR_number>` — reads checkpoint.md and continues from where it stopped
3. Or run `/pipeline "Step N"` — it reads checkpoint.md and skips completed phases

---

## When to use what

| Scenario | Command |
|---|---|
| "Build this one feature" | `/pipeline "Step N — Name"` |
| "Work through the whole plan" | `/orchestrate` |
| "I have a list of bugs to knock out" | `/autopilot --bugs-only` |
| "Run overnight, just fix everything" | `/autopilot --skip-review` |
| "What should I work on?" | `/next` |
| "Show me the plan without running anything" | `/orchestrate --dry-run` |
| "Steps 2 and 3 look independent" | `/orchestrate --parallel` |
