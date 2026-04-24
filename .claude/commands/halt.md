# halt — Gracefully stop the orchestrator

Creates a `.halt` file that the orchestrator checks between phases.
The orchestrator finishes its current phase, then stops cleanly.

No work is lost — checkpoint.md records exactly where it stopped.
Resume with `/orchestrate` or `/resume-pr`.

## Usage

```
/halt                    ← stop after current phase
/halt --reason "scope changed, need to re-plan Step 4"
/halt --cancel           ← remove the halt file, let orchestration continue
```

## Instructions

### If `--cancel`:

```bash
rm -f .halt
```
Print: "Halt cancelled. Orchestration will continue."

### Otherwise:

Create `.halt` with the reason:

```bash
echo "Halted at $(date -u +%Y-%m-%dT%H:%M:%SZ) — Reason: ${REASON:-manual halt}" > .halt
```

Print:
```
⏸ Halt signal created.

The orchestrator will stop after completing its current phase.
No work is lost — checkpoint.md records the exact state.

To resume later:
  rm .halt && /orchestrate    ← continue from where it stopped
  /resume-pr <PR#>            ← if a PR was already open

To cancel the halt:
  /halt --cancel
```

### How the orchestrator uses .halt

The orchestrator checks for `.halt` at these points:
1. Between phases within a step (after Phase 1, 2, 3, etc.)
2. Between steps (after one step merges, before starting the next)
3. Before merging a PR (safety check)

When it sees `.halt`:
1. Writes current state to checkpoint.md
2. Prints what was completed and what's remaining
3. Stops execution
4. Does NOT revert any work — everything committed is preserved
