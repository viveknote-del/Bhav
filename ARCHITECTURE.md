# {{PROJECT_DISPLAY_NAME}} — Architecture

> **Last Updated:** {{DATE}}

## System Overview

[Update this as the system evolves — agents will update this when endpoints or infrastructure changes]

## Services

| Service | Tech | Port | Hosting |
|---|---|---|---|
| Frontend | Next.js 15 | 3000 | Vercel |
| API | FastAPI | 8000 | Render |
| Database | Supabase Postgres | 5432 | Supabase |
| Cache / Queue | Redis | 6379 | Upstash |

## API Endpoints

### Health
- `GET /health` — liveness check

### [Add endpoints as they are built]

## Database Schema

[Add tables as they are created — match migration files in packages/database/migrations/]

## Infrastructure Decisions

| Decision | Choice | Reason |
|---|---|---|
| Auth | Supabase GoTrue | Handles JWT, refresh tokens, RLS |
| Job Queue | arq (Redis-backed) | Lightweight, Python-native |
| Storage | Supabase Storage | Integrated with auth and RLS |
| AI | Claude via providers/llm.py | Single abstraction, easy to swap |
