# {{PROJECT_DISPLAY_NAME}} — Forward Plan

Product roadmap. Steps are the unit of work for `/pipeline`.
Use `/feature` to add new steps. Use `/next` to pick the next step to work on.

---

## Step 0 — Project Scaffold & Setup

**Depends on:** nothing
**Goal:** Working local dev environment with all services running, CI green, basic health endpoint.
**Added:** {{DATE}}

- [ ] Monorepo initialized with pnpm workspaces
- [ ] Next.js 15 frontend scaffold (App Router, Tailwind v3, Supabase auth)
- [ ] FastAPI backend with health endpoint, Pydantic config, layered structure
- [ ] Docker Compose for local Postgres + Redis
- [ ] Supabase project setup (auth, storage, local dev)
- [ ] Initial DB migration
- [ ] GitHub Actions CI (lint, type-check, test)
- [ ] .env.example with all required vars documented
- [ ] Makefile with common dev commands
- [ ] README with setup instructions

## Step 1 — Authentication & User Management

**Depends on:** Step 0
**Goal:** Users can sign up, log in, and have a profile. JWT flows through to the API.
**Added:** {{DATE}}

- [ ] Supabase Auth integrated (email/password, magic link)
- [ ] JWT verification in FastAPI (`auth.py`)
- [ ] User profile table + migration
- [ ] Auth middleware protecting all non-public routes
- [ ] Login and signup pages in Next.js
- [ ] `useAuth` hook for frontend
- [ ] Profile endpoint: `GET /users/me`

## Step 2 — Core Domain (replace with your domain)

**Depends on:** Step 1
**Goal:** [describe the core business object and CRUD operations]
**Added:** {{DATE}}

- [ ] [Item] table + migration
- [ ] CRUD endpoints (list, get, create, update, delete)
- [ ] Router → Service → Repository implementation
- [ ] Pydantic request/response models
- [ ] Frontend list and detail views
- [ ] Unit tests (service layer)
- [ ] Integration tests (API endpoints)

---

*(Add more steps via `/feature` or manually)*
