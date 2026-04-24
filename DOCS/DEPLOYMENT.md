# {{PROJECT_DISPLAY_NAME}} — Deployment

> Last updated: {{DATE}}

## Environments

| Environment | Frontend | Backend | Database |
|---|---|---|---|
| Local | localhost:3000 | localhost:8000 | localhost:5432 |
| Staging | staging.{{PROJECT_NAME}}.com | api-staging.{{PROJECT_NAME}}.com | Supabase staging project |
| Production | {{PROJECT_NAME}}.com | api.{{PROJECT_NAME}}.com | Supabase prod project |

## Local setup

```bash
# 1. Install dependencies
pnpm install
pip install -r services/api/requirements.txt

# 2. Copy env files
cp .env.example .env.local
# Fill in values in .env.local

# 3. Start local services
docker compose up -d

# 4. Run migrations
# Using Supabase local:
supabase start
supabase db reset

# 5. Start dev servers
cd apps/web && pnpm dev          # Frontend: http://localhost:3000
cd services/api && uvicorn main:app --reload --port 8000  # API
```

## Production deployment

### Frontend (Vercel)
- Connects to GitHub main branch
- Auto-deploys on push
- Environment vars set in Vercel dashboard

### Backend (Render)
- Deploy via `render.yaml` or manual dashboard
- Docker-based deployment

### Database (Supabase)
- Migrations run via `supabase db push` or `supabase migration up`
- Always run migrations before deploying new backend

## Deployment checklist

- [ ] Migrations applied to production DB
- [ ] Environment variables updated in all services
- [ ] Backend deployed and health check passes
- [ ] Frontend deployed and loads without errors
- [ ] Smoke test key user flows
