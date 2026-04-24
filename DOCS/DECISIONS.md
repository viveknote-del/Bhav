# {{PROJECT_DISPLAY_NAME}} — Architecture Decisions

Log of significant decisions — what was chosen, what was rejected, and why.

---

## 001 — Monorepo structure

**Decision:** Single pnpm monorepo (`apps/`, `services/`, `packages/`)
**Rejected:** Separate repos per service
**Reason:** Shared types, easier CI, atomic commits across layers

## 002 — Backend layering (Router → Service → Repository)

**Decision:** Strict 3-layer separation in FastAPI
**Reason:** Prevents direct DB calls from route handlers, enables unit testing without DB, makes layer swaps safe

## 003 — Job queue (arq over Celery)

**Decision:** arq for async jobs
**Rejected:** Celery, raw Redis Streams
**Reason:** Lightweight, Python-native, no broker config beyond Redis, type-safe task signatures

## 004 — All AI calls through providers/llm.py

**Decision:** Single abstraction layer for all LLM calls
**Reason:** Easy model swap, consistent retry logic, centralized cost tracking, prevents scattered direct SDK calls

---

*(Add new decisions as they're made during pipeline runs)*
