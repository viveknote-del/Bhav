"""Composite score for a breakout signal.

Score components (each in [0, 1] before weighting):
  - price_strength      : how clean the price break is vs the 52-week range
  - volume_normalized   : how unusual today's volume is on a log scale
  - trend_alignment     : 1.0 if close > 50d MA > 200d MA, partial otherwise
  - atr_clean_break     : break size measured in ATRs
  - pattern_quality     : 0 in this step; Step 3 fills it from detectors/patterns.py

Weights live in WEIGHTS and are intentionally easy to tune from one place.
"""
from __future__ import annotations

import math

import pandas as pd

from services.breakout.types import BreakoutSignal


WEIGHTS = {
    "price_strength":   0.35,
    "volume":           0.25,
    "pattern_quality":  0.20,
    "trend":            0.10,
    "atr_clean_break":  0.10,
}


def _atr(bars: pd.DataFrame, window: int = 14) -> float:
    """Simple Wilder-style ATR over the last `window` bars."""
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


def _price_strength(signal: BreakoutSignal, bars: pd.DataFrame) -> float:
    """Where in the 52-week range did we close? 1.0 = at the top."""
    if len(bars) < 30:
        return 0.5
    lookback = bars.iloc[-min(252, len(bars)):]
    lo = float(lookback["low"].min())
    hi = float(lookback["high"].max())
    if hi <= lo:
        return 0.5
    pos = (signal.price - lo) / (hi - lo)
    return max(0.0, min(1.0, pos))


def _volume_score(signal: BreakoutSignal) -> float:
    """Map volume_ratio (1.0 = average, 5.0 = huge) onto [0, 1] via log."""
    if signal.volume_ratio <= 1.0:
        return 0.0
    # log(5.0) ~= 1.6 saturates near 1.0; ratio of 10 → ~1.0
    return min(1.0, math.log(signal.volume_ratio) / math.log(8.0))


def _trend_alignment(signal: BreakoutSignal, bars: pd.DataFrame) -> float:
    if len(bars) < 200:
        return 0.5
    ma50 = float(bars["close"].iloc[-50:].mean())
    ma200 = float(bars["close"].iloc[-200:].mean())
    if signal.price > ma50 > ma200:
        return 1.0
    if signal.price > ma50:
        return 0.66
    if signal.price > ma200:
        return 0.33
    return 0.0


def _atr_clean_break(signal: BreakoutSignal, bars: pd.DataFrame) -> float:
    """How big is the break vs the symbol's normal range?"""
    if signal.breakout_level is None:
        return 0.5                       # volume-spike etc — neutral
    atr = _atr(bars)
    if atr <= 0:
        return 0.5
    atrs_above = (signal.price - signal.breakout_level) / atr
    return min(1.0, max(0.0, atrs_above / 2.0))


def score(signal: BreakoutSignal, bars: pd.DataFrame, pattern_quality: float = 0.0) -> float:
    """Composite score in [0, 100]."""
    components = {
        "price_strength":  _price_strength(signal, bars),
        "volume":          _volume_score(signal),
        "pattern_quality": max(0.0, min(1.0, pattern_quality)),
        "trend":           _trend_alignment(signal, bars),
        "atr_clean_break": _atr_clean_break(signal, bars),
    }
    weighted = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(weighted * 100, 2)
