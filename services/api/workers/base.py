"""
Base worker with retry, dead-letter queue (DLQ), and job result storage.

All arq workers should inherit from BaseWorker or use the @job decorator.
Never write a bare arq task function without retry + result storage — failed
jobs will disappear silently.

Dead-letter queue: failed jobs (after max_retries) are written to the
`failed_jobs` table in Supabase for human inspection and replay.

Job results: every job writes its outcome to the `job_results` table so
the frontend can poll for completion status.

Usage:
    @job(name="process_item", max_retries=3)
    async def process_item(ctx: dict, item_id: str) -> None:
        item = await get_item(item_id)
        result = await generate_content(item)
        await update_item(item_id, result=result)

The @job decorator handles:
  - Retry with exponential backoff on exception
  - Writing job_results on success
  - Writing to failed_jobs DLQ after max_retries exhausted
"""
import asyncio
import functools
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


def job(name: str, max_retries: int = 3, base_delay: float = 2.0):
    """
    Decorator for arq job functions. Adds retry + DLQ + result storage.

    Args:
        name: unique job name (used as key in job_results table)
        max_retries: how many times to retry before sending to DLQ
        base_delay: seconds for first retry; doubles each attempt (exponential backoff)
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(ctx: dict, *args: Any, **kwargs: Any) -> None:
            db = ctx.get("db")
            job_id = ctx.get("job_id", "unknown")
            attempt = ctx.get("job_try", 1)

            logger.info(
                "job.start",
                extra={"job": name, "job_id": job_id, "attempt": attempt, "args": str(args)[:200]},
            )

            try:
                result = await fn(ctx, *args, **kwargs)

                # Store success
                if db:
                    await _store_result(db, job_id=job_id, job_name=name, status="success", result=result)

                logger.info("job.success", extra={"job": name, "job_id": job_id})

            except Exception as e:
                logger.error(
                    "job.failed",
                    extra={
                        "job": name,
                        "job_id": job_id,
                        "attempt": attempt,
                        "error": str(e),
                        "traceback": traceback.format_exc()[-1000:],
                    },
                )

                if attempt >= max_retries:
                    # Final failure — send to DLQ
                    if db:
                        await _send_to_dlq(
                            db,
                            job_id=job_id,
                            job_name=name,
                            args=args,
                            kwargs=kwargs,
                            error=str(e),
                            traceback_str=traceback.format_exc(),
                        )
                    logger.error(
                        "job.dlq",
                        extra={"job": name, "job_id": job_id, "final_error": str(e)},
                    )
                    # Don't re-raise — arq will not retry further
                    return

                # Exponential backoff before re-raising for arq to retry
                delay = base_delay * (2 ** (attempt - 1))
                logger.info("job.retry", extra={"job": name, "delay_seconds": delay})
                await asyncio.sleep(delay)
                raise  # arq retries based on job_try count

        return wrapper
    return decorator


async def _store_result(db: Any, job_id: str, job_name: str, status: str, result: Any) -> None:
    try:
        db.table("job_results").upsert({
            "job_id": job_id,
            "job_name": job_name,
            "status": status,
            "result": str(result)[:5000] if result else None,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.warning("job.store_result.failed", extra={"error": str(e)})


async def _send_to_dlq(
    db: Any, job_id: str, job_name: str, args: Any, kwargs: Any, error: str, traceback_str: str
) -> None:
    try:
        db.table("failed_jobs").insert({
            "job_id": job_id,
            "job_name": job_name,
            "args": str(args)[:2000],
            "kwargs": str(kwargs)[:2000],
            "error": error[:2000],
            "traceback": traceback_str[-3000:],
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "replayed": False,
        }).execute()
    except Exception as e:
        logger.error("job.dlq.write_failed", extra={"error": str(e)})
