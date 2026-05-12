"""Backtest harness — replay detectors over historical bars and measure
forward-return distributions per detector type.

The engine is provider-agnostic: it pulls bars from the cache layer
(daily_bars), so make sure those are populated first. For NIFTY 50,
seed + an EOD scan or two is enough.

Output is a per-detector summary you can use to tune thresholds and
scoring weights.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import mean
from typing import Iterable

import asyncpg
import pandas as pd

from services.breakout import _swing_filter
from services.breakout.detectors import DETECTORS
from services.breakout.scoring import score as score_signal
from services.breakout.types import BreakoutSignal

logger = logging.getLogger(__name__)


@dataclass
class BacktestSummary:
    detector: str
    n_signals: int = 0
    hit_count: int = 0                 # forward_return > 0
    win_threshold_count: int = 0       # forward_return >= win_threshold
    mean_forward_return: float = 0.0
    mean_composite_score: float = 0.0
    returns: list[float] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        return self.hit_count / self.n_signals if self.n_signals else 0.0

    @property
    def win_rate(self) -> float:
        return self.win_threshold_count / self.n_signals if self.n_signals else 0.0

    def to_dict(self) -> dict:
        return {
            "detector": self.detector,
            "n_signals": self.n_signals,
            "hit_rate": round(self.hit_rate, 3),
            "win_rate": round(self.win_rate, 3),
            "mean_forward_return": round(self.mean_forward_return, 4),
            "mean_composite_score": round(self.mean_composite_score, 2),
        }


async def _load_all_bars(pool: asyncpg.Pool, symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Fetch the entire daily_bars history for each symbol (single round-trip per symbol).
    Caller is expected to have populated bars via scans first."""
    out: dict[str, pd.DataFrame] = {}
    async with pool.acquire() as conn:
        for sym in symbols:
            rows = await conn.fetch(
                """
                SELECT date, open, high, low, close, volume
                  FROM daily_bars
                 WHERE symbol = $1
                 ORDER BY date
                """,
                sym,
            )
            if not rows:
                continue
            df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
            df = df.set_index("date")
            df.index = pd.to_datetime(df.index)
            for col in ("open", "high", "low", "close"):
                df[col] = df[col].astype(float)
            df["volume"] = df["volume"].astype(int)
            out[sym] = df
    return out


def _detector_name(fn) -> str:
    """Detector functions live in submodules; use the module name."""
    return fn.__module__.rsplit(".", 1)[-1]


async def run_backtest(
    pool: asyncpg.Pool,
    symbols: Iterable[str],
    start: date,
    end: date,
    forward_window_days: int = 20,
    win_threshold: float = 0.05,
) -> list[BacktestSummary]:
    """Replay detectors per trading day in [start, end]. For each signal,
    measure forward_return = close[t + forward_window_days] / close[t] - 1.

    Skips signals that don't have enough forward bars.
    """
    symbols = list(symbols)
    bars_by_symbol = await _load_all_bars(pool, symbols)
    logger.info("backtest.loaded", extra={"symbols": len(bars_by_symbol)})

    summaries: dict[str, BacktestSummary] = {
        _detector_name(d): BacktestSummary(detector=_detector_name(d)) for d in DETECTORS
    }

    for symbol, full_bars in bars_by_symbol.items():
        in_range = full_bars[(full_bars.index.date >= start) & (full_bars.index.date <= end)]
        for ts in in_range.index:
            as_of = full_bars.loc[:ts]                  # bars up to and including this date
            if len(as_of) < 30:
                continue
            # Need forward_window_days *trading* bars after `ts` to compute the return
            forward_slice = full_bars.loc[ts:].iloc[1:forward_window_days + 1]
            if len(forward_slice) < forward_window_days:
                continue

            # Swing-trade gate — must mirror production scan_service so the
            # backtest numbers reflect what users will actually see.
            if not _swing_filter.passes(as_of):
                continue

            entry_close = float(as_of["close"].iloc[-1])
            exit_close = float(forward_slice["close"].iloc[-1])
            forward_return = (exit_close - entry_close) / entry_close

            for fn in DETECTORS:
                signal = fn(symbol, as_of)
                if signal is None:
                    continue
                composite = score_signal(signal, as_of)
                summary = summaries[_detector_name(fn)]
                summary.n_signals += 1
                summary.returns.append(forward_return)
                summary.mean_composite_score = (
                    (summary.mean_composite_score * (summary.n_signals - 1) + composite)
                    / summary.n_signals
                )
                if forward_return > 0:
                    summary.hit_count += 1
                if forward_return >= win_threshold:
                    summary.win_threshold_count += 1

    for summary in summaries.values():
        if summary.returns:
            summary.mean_forward_return = mean(summary.returns)

    return list(summaries.values())
