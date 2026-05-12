"""CLI to run the backtest harness over cached daily_bars.

Usage:
    python -m scripts.backtest --start 2025-01-01 --end 2025-04-30
    python -m scripts.backtest --start 2025-01-01 --end 2025-04-30 --forward 10 --win 0.04
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date

import asyncpg

from config import settings
from services.backtest import run_backtest


async def _main(args: argparse.Namespace) -> int:
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=4)
    try:
        async with pool.acquire() as conn:
            symbols = [r["symbol"] for r in await conn.fetch(
                "SELECT symbol FROM instruments WHERE is_active ORDER BY symbol"
            )]
        if not symbols:
            print("No active instruments. Seed first: make seed", file=sys.stderr)
            return 1

        summaries = await run_backtest(
            pool,
            symbols,
            start=date.fromisoformat(args.start),
            end=date.fromisoformat(args.end),
            forward_window_days=args.forward,
            win_threshold=args.win,
        )

        print(f"\nBacktest {args.start} → {args.end}  "
              f"(forward {args.forward}d, win threshold {args.win:.0%})")
        print(f"Universe: {len(symbols)} symbols\n")
        print(f"{'Detector':<24} {'N':>6} {'Hit %':>8} {'Win %':>8} "
              f"{'Mean Fwd':>10} {'Mean Score':>12}")
        print("─" * 70)
        for s in summaries:
            print(
                f"{s.detector:<24} {s.n_signals:>6d} "
                f"{s.hit_rate * 100:>7.1f}% {s.win_rate * 100:>7.1f}% "
                f"{s.mean_forward_return * 100:>9.2f}% "
                f"{s.mean_composite_score:>12.2f}"
            )
        return 0
    finally:
        await pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="ISO date (e.g. 2025-01-01)")
    parser.add_argument("--end", required=True, help="ISO date (e.g. 2025-04-30)")
    parser.add_argument("--forward", type=int, default=20,
                        help="Forward window in trading days (default 20)")
    parser.add_argument("--win", type=float, default=0.05,
                        help="Win threshold for forward return (default 0.05 = 5%%)")
    args = parser.parse_args()
    sys.exit(asyncio.run(_main(args)))
