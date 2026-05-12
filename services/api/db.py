"""Async Postgres connection pool used by all repositories.

The pool is opened in the FastAPI lifespan (see main.py) and shared
across requests. Routers/services receive it via the `get_pool` FastAPI
dependency.
"""
from __future__ import annotations

import asyncpg
from fastapi import FastAPI, Request

from config import settings


async def open_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        settings.database_url,
        min_size=1,
        max_size=10,
        command_timeout=10,
    )


async def close_pool(pool: asyncpg.Pool) -> None:
    await pool.close()


def attach_pool(app: FastAPI, pool: asyncpg.Pool) -> None:
    app.state.pool = pool


def get_pool(request: Request) -> asyncpg.Pool:
    """FastAPI dependency — returns the shared pool."""
    return request.app.state.pool
