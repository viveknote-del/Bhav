from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import attach_pool, close_pool, open_pool
from routers import charts, health, instruments


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_config()
    pool = await open_pool()
    attach_pool(app, pool)
    try:
        yield
    finally:
        await close_pool(pool)


def _validate_config() -> None:
    """Fail fast on startup if required config is missing."""
    required = [
        ("DATABASE_URL", settings.database_url),
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

    app.include_router(health.router)
    app.include_router(instruments.router)
    app.include_router(charts.router)

    return app


app = create_app()
