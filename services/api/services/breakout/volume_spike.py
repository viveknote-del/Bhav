"""Volume spike detector.

Fires when today's volume is multiple times its 20-day average AND
the bar closes positive. Catches sudden interest before a 52w-high
break has fully formed.
"""
from __future__ import annotations

import pandas as pd

from services.breakout.types import BreakoutSignal

MIN_HISTORY = 25                     # need >= 21 bars for the 20d window + today
SPIKE_RATIO = 3.0                    # today's volume must be >= 3× 20d avg
MIN_POSITIVE_CLOSE_PCT = 0.005       # bar must close at least 0.5% above the day's open


def detect(symbol: str, bars: pd.DataFrame) -> BreakoutSignal | None:
    if len(bars) < MIN_HISTORY:
        return None

    bars = bars.sort_index()
    today = bars.iloc[-1]

    if today["open"] <= 0:
        return None
    close_pct = (float(today["close"]) - float(today["open"])) / float(today["open"])
    if close_pct < MIN_POSITIVE_CLOSE_PCT:
        return None

    avg_vol_20 = float(bars["volume"].iloc[-21:-1].mean())
    if avg_vol_20 <= 0:
        return None
    volume_ratio = float(today["volume"]) / avg_vol_20
    if volume_ratio < SPIKE_RATIO:
        return None

    return BreakoutSignal(
        symbol=symbol,
        breakout_type="VOLUME_SPIKE",
        price=float(today["close"]),
        breakout_level=None,             # not a price-level break
        volume_ratio=volume_ratio,
        indicators={
            "close_pct": close_pct,
            "avg_vol_20": avg_vol_20,
        },
    )
