from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arq_client import attach_arq, close_arq, open_arq
from config import settings
from db import attach_pool, close_pool, open_pool
from routers import backtests, breakouts, charts, health, instruments, scans, watchlist


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_config()
    pool = await open_pool()
    arq = await open_arq()
    attach_pool(app, pool)
    attach_arq(app, arq)
    try:
        yield
    finally:
        await close_arq(arq)
        await close_pool(pool)


def _validate_config() -> None:
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
    app.include_router(scans.router)
    app.include_router(breakouts.router)
    app.include_router(watchlist.router)
    app.include_router(backtests.router)

    return app


app = create_app()
