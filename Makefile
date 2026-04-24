.PHONY: help dev up down logs api-test web-test e2e migrate lint typecheck

help:
	@echo "Available commands:"
	@echo "  make up          — Start local services (Postgres + Redis)"
	@echo "  make down        — Stop local services"
	@echo "  make dev         — Start frontend dev server"
	@echo "  make api         — Start backend dev server"
	@echo "  make api-test    — Run backend tests"
	@echo "  make web-test    — Run frontend tests"
	@echo "  make e2e         — Run Playwright E2E tests"
	@echo "  make lint        — Run frontend lint"
	@echo "  make typecheck   — Run TypeScript type check"
	@echo "  make sanity      — Health check all services"
	@echo "  make migrate     — Apply DB migrations"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

dev:
	cd apps/web && pnpm dev

api:
	cd services/api && uvicorn main:app --reload --port 8000

api-test:
	cd services/api && python -m pytest -v

web-test:
	cd apps/web && pnpm test

e2e:
	cd apps/web && pnpm playwright test

lint:
	cd apps/web && pnpm lint

typecheck:
	cd apps/web && pnpm tsc --noEmit

sanity:
	./scripts/sanity-check.sh

migrate:
	@echo "Apply migrations via Supabase CLI:"
	@echo "  supabase db push    (for hosted Supabase)"
	@echo "  supabase db reset   (for local Supabase)"

evals:
	cd services/api && python -m evals.runner

evals-ci:
	cd services/api && python -m evals.runner --ci

pre-commit-install:
	pip install pre-commit && pre-commit install

pre-commit-run:
	pre-commit run --all-files

cost-report:
	@echo "Query your logs for 'llm.usage' events to see token spend."
	@echo "Or run: grep 'llm.usage' logs/api.log | jq ."
