"""@job decorator with retry, dead-letter queue, and result storage.

All arq jobs go through this decorator. Failed jobs land in `failed_jobs`
table for inspection; successful job outcomes land in `job_results`.

The decorated function receives the arq `ctx` dict; we expect ctx['pool']
to hold an asyncpg.Pool. Workers init that in WorkerSettings.startup.

Usage:
    @job(name="scan_eod", max_retries=3)
    async def scan_eod(ctx, scan_run_id: str) -> None:
        pool = ctx["pool"]
        ...
"""
from __future__ import annotations

import asyncio
import functools
import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Callable

import asyncpg

logger = logging.getLogger(__name__)


def job(name: str, max_retries: int = 3, base_delay: float = 2.0):
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(ctx: dict, *args: Any, **kwargs: Any) -> None:
            pool: asyncpg.Pool | None = ctx.get("pool")
            job_id = ctx.get("job_id", "unknown")
            attempt = ctx.get("job_try", 1)

            logger.info(
                "job.start",
                extra={"job": name, "job_id": job_id, "attempt": attempt},
            )

            try:
                result = await fn(ctx, *args, **kwargs)
                if pool is not None:
                    await _store_result(pool, job_id=job_id, job_name=name, status="success", result=result)
                logger.info("job.success", extra={"job": name, "job_id": job_id})

            except Exception as e:
                logger.error(
                    "job.failed",
                    extra={
                        "job": name,
                        "job_id": job_id,
                        "attempt": attempt,
                        "error": str(e),
                    },
                )

                if attempt >= max_retries:
                    if pool is not None:
                        await _send_to_dlq(
                            pool,
                            job_id=job_id,
                            job_name=name,
                            args=args,
                            kwargs=kwargs,
                            error=str(e),
                            traceback_str=traceback.format_exc(),
                        )
                    logger.error("job.dlq", extra={"job": name, "job_id": job_id})
                    return

                delay = base_delay * (2 ** (attempt - 1))
                logger.info("job.retry", extra={"job": name, "delay_seconds": delay})
                await asyncio.sleep(delay)
                raise

        return wrapper
    return decorator


async def _store_result(
    pool: asyncpg.Pool, job_id: str, job_name: str, status: str, result: Any
) -> None:
    try:
        result_text = json.dumps(result, default=str)[:5000] if result is not None else None
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO job_results (job_id, job_name, status, result, completed_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (job_id) DO UPDATE
                  SET status = EXCLUDED.status,
                      result = EXCLUDED.result,
                      completed_at = EXCLUDED.completed_at
                """,
                job_id, job_name, status, result_text, datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.warning("job.store_result.failed", extra={"error": str(e)})


async def _send_to_dlq(
    pool: asyncpg.Pool,
    job_id: str,
    job_name: str,
    args: Any,
    kwargs: Any,
    error: str,
    traceback_str: str,
) -> None:
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO failed_jobs (job_id, job_name, args, kwargs, error, traceback, failed_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                job_id,
                job_name,
                str(args)[:2000],
                str(kwargs)[:2000],
                error[:2000],
                traceback_str[-3000:],
                datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error("job.dlq.write_failed", extra={"error": str(e)})
