"""Evaluate alert rules against a scan's top breakouts and dispatch.

Rule (configurable via env):
  composite_score >= settings.alert_min_score
  AND breakout_type in {FIFTY_TWO_WEEK_HIGH, CONSOLIDATION}
  AND alerted_at IS NULL (skip already-alerted)

Each qualifying breakout fires one Telegram message containing the
symbol, score, breakout type, price, and the Claude commentary if
available. Marked alerted_at after a successful send so a rerun doesn't
re-spam.
"""
from __future__ import annotations

import logging
from uuid import UUID

import asyncpg

from config import settings
from providers.alerts import send_telegram

logger = logging.getLogger(__name__)

ALERTABLE_TYPES = {"FIFTY_TWO_WEEK_HIGH", "CONSOLIDATION"}


def _format_message(row: asyncpg.Record) -> str:
    score = int(round(float(row["composite_score"])))
    type_label = row["breakout_type"].replace("_", " ").title()
    name = row["instrument_name"] if "instrument_name" in row.keys() else row["symbol"]
    price = float(row["price"])
    vol = float(row["volume_ratio"]) if row["volume_ratio"] is not None else 0.0

    header = (
        f"🟢 *Bhav alert* — `{row['symbol']}` ({name})\n"
        f"{type_label} · score *{score}/100* · ₹{price:,.2f} · {vol:.1f}× vol\n"
    )
    if row["ai_commentary"]:
        return header + "\n" + row["ai_commentary"]
    return header


async def evaluate_and_alert(pool: asyncpg.Pool, scan_run_id: UUID) -> int:
    """Returns the count of alerts sent for this scan."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return 0

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT b.id, b.symbol, b.breakout_type, b.price, b.volume_ratio,
                   b.composite_score, b.ai_commentary,
                   i.name AS instrument_name
              FROM breakouts b
              JOIN instruments i ON i.symbol = b.symbol
             WHERE b.scan_run_id = $1
               AND b.composite_score >= $2
               AND b.breakout_type = ANY($3::text[])
               AND b.alerted_at IS NULL
             ORDER BY b.composite_score DESC
            """,
            scan_run_id, float(settings.alert_min_score), list(ALERTABLE_TYPES),
        )

    sent = 0
    for row in rows:
        delivered = await send_telegram(_format_message(row))
        if delivered:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE breakouts SET alerted_at = now() WHERE id = $1",
                    row["id"],
                )
            sent += 1

    if sent:
        logger.info("alerts.sent", extra={"scan_id": str(scan_run_id), "count": sent})
    return sent
