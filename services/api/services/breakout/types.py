"""Shared types for the breakout detection layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

BreakoutType = Literal["FIFTY_TWO_WEEK_HIGH", "CONSOLIDATION", "VOLUME_SPIKE", "PATTERN"]
PatternSubtype = Literal["FLAG", "CUP_HANDLE", "TRIANGLE"]


@dataclass(frozen=True)
class BreakoutSignal:
    """A detector's verdict for one symbol on one bar.

    Detectors return this (or None) and remain pure — no DB, no IO.
    The scorer composes a `composite_score`; persistence is the caller's job.
    """
    symbol: str
    breakout_type: BreakoutType
    price: float                       # the bar's close
    breakout_level: float | None       # the level that was broken (e.g. prior 52w high)
    volume_ratio: float                # today_vol / avg_20d_vol
    pattern_subtype: PatternSubtype | None = None
    indicators: dict = field(default_factory=dict)
