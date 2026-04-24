# routers

Add files here following the pattern from `routers/health.py`.

Layer rules (see CLAUDE.md for full conventions):
- Routers: HTTP in/out, auth guard, call service
- Services: business logic, orchestrate calls
- Repositories: raw DB queries via supabase-py
- Models: Pydantic request/response types
- Workers: arq async job handlers
