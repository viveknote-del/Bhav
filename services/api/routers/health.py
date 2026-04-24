import logging
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config import settings

router = APIRouter(prefix="/v1/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("")
async def health_check():
    """
    Liveness + dependency health check.

    Returns 200 if all critical dependencies are reachable.
    Returns 503 if any critical dependency is down.
    Frontend and load balancers should poll this.
    """
    checks: dict[str, dict] = {}
    overall = "ok"

    # Database check
    t0 = time.monotonic()
    try:
        from supabase import create_client
        db = create_client(settings.supabase_url, settings.supabase_service_role_key)
        db.table("profiles").select("id").limit(1).execute()
        checks["database"] = {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)[:100]}
        overall = "degraded"
        logger.error("health.database.failed", extra={"error": str(e)})

    # Redis check
    t0 = time.monotonic()
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url, socket_timeout=2)
        r.ping()
        checks["redis"] = {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)[:100]}
        overall = "degraded"
        logger.error("health.redis.failed", extra={"error": str(e)})

    # AI provider check (non-critical — degraded, not down)
    checks["ai_provider"] = {
        "status": "configured" if settings.anthropic_api_key else "unconfigured",
        "primary": "anthropic",
        "fallback": "openai" if settings.openai_api_key else "none",
    }

    status_code = 200 if overall == "ok" else 503
    return JSONResponse({"status": overall, "checks": checks}, status_code=status_code)


@router.get("/ping")
async def ping():
    """Minimal liveness probe — no dependency checks. Use for k8s liveness probe."""
    return {"status": "ok"}
