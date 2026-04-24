# AI Starter Kit

A battle-tested monorepo template for AI-first product development with full Claude Code orchestration. Derived from two production apps (TixReady + Marketing Agency Platform).

## Usage

### Personalize for a new project

```bash
cp -r ~/projects/ai-starter ~/projects/your-project
cd ~/projects/your-project

# Replace all {{PLACEHOLDER}} values
./scripts/setup.sh
```

### Placeholders to replace

| Placeholder | Example |
|---|---|
| `{{PROJECT_NAME}}` | `tixready` |
| `{{PROJECT_DISPLAY_NAME}}` | `TixReady` |
| `{{PROJECT_DESCRIPTION}}` | `Premium ticketing platform for exclusive events` |
| `{{DB_NAME}}` | `myproject` |
| `{{GITHUB_REPO}}` | `username/repo-name` |

## Structure

```
.
├── CLAUDE.md                  ← AI context brain — update first
├── ARCHITECTURE.md            ← Living architecture doc
├── .claude/
│   ├── settings.json          ← Permissions + /approve merge gate
│   └── commands/              ← /next /pipeline /bug /feature /resume-pr
├── DOCS/
│   ├── KANBAN.md              ← Task board (agents update this)
│   ├── BUGS.md                ← Bug tracker
│   ├── DEFERRED.md            ← Punted items
│   ├── BACKLOG.md             ← Feature requests
│   ├── DECISIONS.md           ← Architecture decisions
│   ├── DEPLOYMENT.md          ← Deployment runbook
│   ├── pipeline/              ← Per-step docs (agents write here)
│   ├── CODE-STANDARDS.md      ← naming, patterns, testing rules (read on demand)
│   ├── PATTERNS.md            ← design patterns reference (read on demand)
│   └── AI-FIRST.md            ← token strategy, model routing, caching guide
├── plans/forward.md           ← Product roadmap (steps for /pipeline)
├── apps/web/                  ← Next.js 15 frontend
├── services/api/              ← FastAPI backend (Router→Service→Repo)
├── packages/                  ← Shared types + DB migrations
├── docker-compose.yml         ← Local dev (Postgres + Redis)
├── Makefile                   ← Common dev commands
└── .github/workflows/ci.yml   ← CI
```

## Workflow

```
/next                          → prioritized work menu (bugs + steps + deferrals)
/pipeline "Step N — Name"      → full SDLC cycle for one step
/bug "description"             → triage and log to DOCS/BUGS.md
/feature "idea"                → intake a feature into plans/forward.md
/resume-pr <PR#>               → pick up a stalled pipeline
/trim                          → archive completed items, check CLAUDE.md size
```

## Key design decisions

- **Model routing** — Haiku for routine implementation (~1/20th cost), Opus for design/requirements, Sonnet for everything else. Opus auto-escalates on test failure.
- **/approve gate** — PRs cannot merge until a human posts `/approve` as a GitHub comment. Hook blocks it at the Bash level.
- **No direct push to main** — settings.json blocks `git push origin main`.
- **Per-step DOCS/** — Every pipeline run writes `requirements.md`, `design.md`, `issues.md`, `testing.md`, `summary.md` to `DOCS/pipeline/step-N/`. This is the AI memory across sessions.
- **DEFERRED.md limit** — Items deferred 3+ times auto-become blockers for the next step.
