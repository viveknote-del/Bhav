from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate required env vars, warm connections
    _validate_config()
    yield
    # Shutdown: nothing to clean up


def _validate_config() -> None:
    """Fail fast on startup if required config is missing."""
    required = [
        ("SUPABASE_URL", settings.supabase_url),
        ("SUPABASE_SERVICE_ROLE_KEY", settings.supabase_service_role_key),
        ("JWT_SECRET", settings.jwt_secret),
        ("REDIS_URL", settings.redis_url),
    ]
    missing = [name for name, val in required if not val]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill in all values."
        )


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        # Disable docs in production
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers — all routes are versioned under /v1/
    app.include_router(health.router)
    # app.include_router(items.router)  ← add domain routers here

    return app


app = create_app()
