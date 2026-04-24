## What

<!-- One paragraph: what changed and why. Not how — the diff shows that. -->

## Type

- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Docs
- [ ] Infra / config

## Test plan

<!-- How did you verify this works? Copy-pasteable commands preferred. -->

- [ ] Backend tests pass: `cd services/api && pytest -v`
- [ ] Frontend build clean: `cd apps/web && pnpm build`
- [ ] TypeScript clean: `cd apps/web && pnpm tsc --noEmit`
- [ ] Manual smoke test: [describe what you clicked/called]

## AI checklist

<!-- Only fill this in if you changed a prompt or AI provider code. -->

- [ ] No prompt changes — skip this section
- [ ] Changed prompt(s): [list which ones in `prompts/registry.py`]
- [ ] Ran evals: `cd services/api && python -m evals.runner`
- [ ] Eval score: [N/N passed]
- [ ] Compared output before/after: [paste 1-2 example outputs or "no regression"]

## Deferred

<!-- Anything intentionally left out of this PR with a reason. -->

- None

## Screenshots

<!-- For UI changes. Before + after at 375px and 1440px. -->
