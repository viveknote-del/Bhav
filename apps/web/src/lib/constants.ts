// Defaults to :8765 because :8000 collides with common defaults on dev
// machines (Postgres clients, FastAPI tutorials, Docker Compose templates).
// Override via NEXT_PUBLIC_API_URL in apps/web/.env.local if needed.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8765'
