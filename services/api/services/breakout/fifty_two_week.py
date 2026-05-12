"""52-week high breakout detector.

Fires when today's close exceeds the prior 252-trading-day high by a
configurable buffer AND volume is above its 20-day average (filters
breakouts on dead volume that tend to fail).
"""
from __future__ import annotations

import pandas as pd

from services.breakout.types import BreakoutSignal

MIN_HISTORY = 252                    # need at least one full year of history
PRICE_BUFFER = 0.005                 # 0.5% above prior high to count
VOLUME_FLOOR_RATIO = 1.2             # today's volume >= 1.2× 20d avg


def detect(symbol: str, bars: pd.DataFrame) -> BreakoutSignal | None:
    if len(bars) < MIN_HISTORY:
        return None

    bars = bars.sort_index()
    today = bars.iloc[-1]
    prior = bars.iloc[-MIN_HISTORY:-1]                    # exclude today
    prior_high = float(prior["close"].max())

    if today["close"] <= prior_high * (1 + PRICE_BUFFER):
        return None

    avg_vol_20 = float(bars["volume"].iloc[-21:-1].mean())  # 20 trading days excluding today
    if avg_vol_20 <= 0:
        return None
    volume_ratio = float(today["volume"]) / avg_vol_20
    if volume_ratio < VOLUME_FLOOR_RATIO:
        return None

    return BreakoutSignal(
        symbol=symbol,
        breakout_type="FIFTY_TWO_WEEK_HIGH",
        price=float(today["close"]),
        breakout_level=prior_high,
        volume_ratio=volume_ratio,
        indicators={
            "prior_high": prior_high,
            "break_pct": (float(today["close"]) - prior_high) / prior_high,
            "avg_vol_20": avg_vol_20,
        },
    )
