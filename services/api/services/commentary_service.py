"""Commentary orchestration: signal → news context → Claude → persist.

Two entry points:
- `generate_for_breakout` writes commentary on a single breakout.
- `generate_eod_digest` writes the once-per-scan top-5 digest onto
  `scan_runs.summary`.

Both are cost-bounded: per-breakout commentary only runs for the top N
(see settings.commentary_top_n). The EOD digest is one Claude call per scan.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Sequence
from uuid import UUID

import asyncpg

from config import settings
from models.scan import BreakoutOut
from providers import llm
from providers.news import Headline, get_headlines
from repositories import breakout_repo, scan_repo

logger = logging.getLogger(__name__)


# ──────────────────── context composition ──────────────────────

def _format_indicators(indicators: dict | None) -> str:
    if not indicators:
        return "(none)"
    parts: list[str] = []
    for k, v in indicators.items():
        if isinstance(v, float):
            parts.append(f"{k}={v:.3g}")
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)


def _format_headlines(headlines: Sequence[Headline]) -> str:
    if not headlines:
        return "Recent headlines (last 3 days): none relevant"
    lines = ["Recent headlines (last 3 days):"]
    for h in headlines:
        lines.append(f'- "{h.title}" ({h.source})')
    return "\n".join(lines)


def _build_breakout_context(row: asyncpg.Record, headlines: Sequence[Headline]) -> str:
    """Compose the per-breakout context that gets sent to Claude as the
    user message. Mirrors the few-shot example format in prompts/registry.py."""
    indicators = row["indicators"]
    if isinstance(indicators, str):
        indicators = json.loads(indicators)

    name = row.get("instrument_name") or row["symbol"]
    sector = row.get("instrument_sector") or "Unknown sector"

    break_line = ""
    if row["breakout_level"] is not None:
        diff_pct = ((float(row["price"]) - float(row["breakout_level"])) / float(row["breakout_level"])) * 100
        break_line = f" (broke prior level of ₹{float(row['breakout_level']):.2f} by {diff_pct:+.1f}%)"

    subtype_line = f"\nPattern subtype: {row['pattern_subtype']}" if row["pattern_subtype"] else ""
    volume_ratio = float(row["volume_ratio"]) if row["volume_ratio"] is not None else 0.0

    return (
        f"Symbol: {row['symbol']} ({name} — {sector})\n"
        f"Breakout type: {row['breakout_type']}{subtype_line}\n"
        f"Price: ₹{float(row['price']):.2f}{break_line}\n"
        f"Volume ratio: {volume_ratio:.1f}× 20-day average\n"
        f"Composite score: {float(row['composite_score']):.0f}\n"
        f"Indicators: {_format_indicators(indicators)}\n"
        f"{_format_headlines(headlines)}\n"
    )


def _build_digest_context(scan_date: date, top_breakouts: Sequence[asyncpg.Record]) -> str:
    lines = [f"Top {len(top_breakouts)} breakouts on {scan_date.isoformat()} (Bhav scan, NIFTY 50 universe):"]
    for i, b in enumerate(top_breakouts, start=1):
        name = b.get("instrument_name") or b["symbol"]
        sector = b.get("instrument_sector") or "Unknown sector"
        subtype = f"/{b['pattern_subtype']}" if b["pattern_subtype"] else ""
        volume_ratio = float(b["volume_ratio"]) if b["volume_ratio"] is not None else 0.0
        lines.append(
            f"{i}. {b['symbol']} ({sector}) — {b['breakout_type']}{subtype}, "
            f"score {float(b['composite_score']):.0f}, "
            f"volume {volume_ratio:.1f}×, "
            f"price ₹{float(b['price']):.2f} ({name})"
        )
    return "\n".join(lines) + "\n"


# ──────────────────── public entry points ──────────────────────

async def generate_for_breakout(
    pool: asyncpg.Pool,
    breakout_id: UUID,
    *,
    force_news_refresh: bool = False,
) -> str:
    """Generate and persist commentary for a single breakout. Returns the text."""
    row = await breakout_repo.get_breakout(pool, breakout_id)
    if row is None:
        raise ValueError(f"Breakout {breakout_id} not found")

    inst_name, inst_sector = await _instrument_lookup(pool, row["symbol"])
    # Make a mutable dict so _build_breakout_context can read both row + instrument
    ctx_row = dict(row)
    ctx_row["instrument_name"] = inst_name
    ctx_row["instrument_sector"] = inst_sector

    scan_date = (row["detected_at"] or row["created_at"] if "created_at" in row else None)
    if hasattr(scan_date, "date"):
        scan_date_only = scan_date.date()
    else:
        scan_date_only = date.today()

    headlines = await get_headlines(
        pool, row["symbol"], inst_name, scan_date_only, force_refresh=force_news_refresh
    )

    user_message = _build_breakout_context(ctx_row, headlines)
    result = await llm.generate("breakout_commentary", user_message)

    await breakout_repo.update_commentary(
        pool,
        breakout_id,
        commentary=result.text,
        news_links=[h.as_dict() for h in headlines] if headlines else None,
    )
    logger.info(
        "commentary.generated",
        extra={
            "breakout_id": str(breakout_id),
            "symbol": row["symbol"],
            "cost_usd": result.usage.cost_usd,
        },
    )
    return result.text


async def generate_for_top_n(pool: asyncpg.Pool, scan_run_id: UUID) -> int:
    """Generate commentary for the top N breakouts of a scan. Returns count.

    N comes from settings.commentary_top_n (default 20). Bounds spend.
    """
    rows = await breakout_repo.top_breakouts_for_scan(
        pool, scan_run_id, settings.commentary_top_n
    )
    count = 0
    for row in rows:
        try:
            await generate_for_breakout(pool, row["id"])
            count += 1
        except Exception as e:                          # noqa: BLE001
            logger.warning(
                "commentary.symbol_failed",
                extra={"breakout_id": str(row["id"]), "symbol": row["symbol"], "error": str(e)},
            )
    return count


async def generate_eod_digest(pool: asyncpg.Pool, scan_run_id: UUID) -> str | None:
    """Write the once-per-scan top-5 summary onto scan_runs.summary."""
    rows = await breakout_repo.top_breakouts_for_scan(pool, scan_run_id, 5)
    if not rows:
        return None

    scan = await scan_repo.get_scan(pool, scan_run_id)
    scan_date = scan["started_at"].date() if scan else date.today()

    user_message = _build_digest_context(scan_date, rows)
    result = await llm.generate("eod_digest", user_message)
    await scan_repo.update_summary(pool, scan_run_id, result.text)
    return result.text


# ──────────────────── internals ──────────────────────

async def _instrument_lookup(pool: asyncpg.Pool, symbol: str) -> tuple[str | None, str | None]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT name, sector FROM instruments WHERE symbol = $1", symbol
        )
    if row is None:
        return None, None
    return row["name"], row["sector"]
