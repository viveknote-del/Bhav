"""Consolidation breakout detector.

Fires when:
  - today's close breaks above the 20-day Donchian top
  - the prior 20-day range was "tight" — range / ATR(14) below a threshold,
    measuring that price was coiling, not just choppy
  - volume on the break is above the consolidation's average volume

Tighter consolidations get higher pattern_quality scores.
"""
from __future__ import annotations

import pandas as pd

from services.breakout._ta import atr, donchian
from services.breakout.types import BreakoutSignal

CONSOLIDATION_WINDOW = 20
MIN_HISTORY = 50
PRICE_BUFFER = 0.005                # 0.5% above prior top (was 0.3%, consistency)
MAX_TIGHTNESS = 5.0                 # range / ATR(14); lower = tighter
GOOD_TIGHTNESS = 2.5                # tightness <= this → pattern_quality 1.0
VOLUME_FLOOR_RATIO = 1.5            # 1.5× consolidation avg (was 1.3, consistency)


def _tightness(bars_window: pd.DataFrame, atr_14: float) -> float:
    if atr_14 <= 0:
        return float("inf")
    rng = float(bars_window["high"].max() - bars_window["low"].min())
    return rng / atr_14


def _quality_from_tightness(t: float) -> float:
    """Maps tightness onto [0, 1]; tighter = closer to 1."""
    if t <= GOOD_TIGHTNESS:
        return 1.0
    if t >= MAX_TIGHTNESS:
        return 0.0
    return 1.0 - (t - GOOD_TIGHTNESS) / (MAX_TIGHTNESS - GOOD_TIGHTNESS)


def detect(symbol: str, bars: pd.DataFrame) -> BreakoutSignal | None:
    if len(bars) < MIN_HISTORY:
        return None

    bars = bars.sort_index()
    today = bars.iloc[-1]

    donchian_top, _ = donchian(bars, CONSOLIDATION_WINDOW)
    if donchian_top <= 0 or today["close"] <= donchian_top * (1 + PRICE_BUFFER):
        return None

    consolidation_window = bars.iloc[-(CONSOLIDATION_WINDOW + 1):-1]
    atr_14 = atr(bars.iloc[:-1], window=14)
    tightness = _tightness(consolidation_window, atr_14)
    if tightness > MAX_TIGHTNESS:
        return None                              # too wide — not really a consolidation

    avg_vol = float(consolidation_window["volume"].mean())
    if avg_vol <= 0:
        return None
    volume_ratio = float(today["volume"]) / avg_vol
    if volume_ratio < VOLUME_FLOOR_RATIO:
        return None

    quality = _quality_from_tightness(tightness)

    return BreakoutSignal(
        symbol=symbol,
        breakout_type="CONSOLIDATION",
        price=float(today["close"]),
        breakout_level=donchian_top,
        volume_ratio=volume_ratio,
        pattern_quality=quality,
        indicators={
            "donchian_top": donchian_top,
            "tightness": tightness,
            "atr_14": atr_14,
            "consolidation_avg_volume": avg_vol,
        },
    )
