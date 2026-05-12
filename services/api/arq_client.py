"""Arq Redis client used by the API to enqueue jobs.

The API process and the worker process talk via the same Redis. The API
only enqueues; actual execution happens in the worker (workers/__init__.py).
"""
from __future__ import annotations

from urllib.parse import urlparse

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import FastAPI, Request

from config import settings


def redis_settings() -> RedisSettings:
    u = urlparse(settings.redis_url)
    return RedisSettings(
        host=u.hostname or "localhost",
        port=u.port or 6379,
        password=u.password,
        database=int(u.path.lstrip("/")) if u.path and u.path != "/" else 0,
    )


async def open_arq() -> ArqRedis:
    return await create_pool(redis_settings())


async def close_arq(arq: ArqRedis) -> None:
    await arq.aclose()


def attach_arq(app: FastAPI, arq: ArqRedis) -> None:
    app.state.arq = arq


def get_arq(request: Request) -> ArqRedis:
    return request.app.state.arq
