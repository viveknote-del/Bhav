"""Tiny TA helpers shared by detectors and scoring.

Keeping these inline (vs depending on `ta` or `talipp`) keeps Step 3
honest: we know exactly what each indicator does, no surprise behaviour.
"""
from __future__ import annotations

import pandas as pd


def atr(bars: pd.DataFrame, window: int = 14) -> float:
    """Wilder-style ATR over the trailing `window` bars."""
    if len(bars) < window + 1:
        return 0.0
    high = bars["high"]
    low = bars["low"]
    prev_close = bars["close"].shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return float(tr.iloc[-window:].mean())


def donchian(bars: pd.DataFrame, window: int = 20) -> tuple[float, float]:
    """Top and bottom of the Donchian channel over the trailing `window`
    bars EXCLUDING today (so 'today breaks out' is well-defined)."""
    if len(bars) < window + 1:
        return 0.0, 0.0
    window_slice = bars.iloc[-(window + 1):-1]
    return float(window_slice["high"].max()), float(window_slice["low"].min())
