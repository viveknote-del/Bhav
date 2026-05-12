"""Swing-trade pre-gate applied PER SYMBOL before detectors run.

If the symbol fails this gate, no detector will fire on it for this scan.
This is the single biggest swing-trading filter — most failed breakouts
happen in downtrends, choppy markets, or already-extended momentum runs.

Sourced from mainstream swing-trading consensus (golden cross / 50 SMA
trend confirmation, RSI momentum range, ADX trend-strength filter).

The thresholds are tuned conservatively. If the backtest shows we're
filtering out genuine winners, loosen them; if it shows too many false
positives still slipping through, tighten them.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from services.breakout._ta import adx, rsi, sma

# Hard cutoffs. See the DeepSeek swing-trading checklist comparison in
# the commit message that introduced this file.
MIN_HISTORY = 200          # need 200 bars to compute 200d SMA
RSI_MIN = 55
RSI_MAX = 85
ADX_MIN = 25


@dataclass(frozen=True)
class SwingIndicators:
    price: float
    sma_50: float
    sma_200: float
    rsi_14: float
    adx_14: float
    passed: bool
    reason: str | None         # why it failed, or None when passed

    def as_dict(self) -> dict:
        return {
            "price": round(self.price, 4),
            "sma_50": round(self.sma_50, 4),
            "sma_200": round(self.sma_200, 4),
            "rsi_14": round(self.rsi_14, 2),
            "adx_14": round(self.adx_14, 2),
            "swing_passed": self.passed,
            "swing_reason": self.reason,
        }


def evaluate(bars: pd.DataFrame) -> SwingIndicators:
    """Compute the swing-trade indicators and reject reason (if any).

    Always returns a `SwingIndicators` — `.passed` says whether the bar
    is swing-tradeable. Callers can persist the indicators even on a
    rejection if they want the data for diagnostics.
    """
    if len(bars) < MIN_HISTORY:
        return SwingIndicators(0.0, 0.0, 0.0, 50.0, 0.0, False, "insufficient_history")

    bars = bars.sort_index()
    price = float(bars["close"].iloc[-1])
    sma_50 = sma(bars, 50)
    sma_200 = sma(bars, 200)
    rsi_14 = rsi(bars, 14)
    adx_14 = adx(bars, 14)

    # Trend filter: price above 50d MA above 200d MA (the "golden cross"
    # ordering as a continuous, not just a one-time event).
    if not (price > sma_50 > sma_200):
        return SwingIndicators(price, sma_50, sma_200, rsi_14, adx_14, False, "downtrend")

    # Momentum filter: RSI in the strong-but-not-overbought zone.
    if rsi_14 < RSI_MIN:
        return SwingIndicators(price, sma_50, sma_200, rsi_14, adx_14, False, "rsi_weak")
    if rsi_14 > RSI_MAX:
        return SwingIndicators(price, sma_50, sma_200, rsi_14, adx_14, False, "rsi_extended")

    # Trend STRENGTH filter: ADX > 25 means we're actually trending,
    # not just floating through chop.
    if adx_14 < ADX_MIN:
        return SwingIndicators(price, sma_50, sma_200, rsi_14, adx_14, False, "adx_choppy")

    return SwingIndicators(price, sma_50, sma_200, rsi_14, adx_14, True, None)


def passes(bars: pd.DataFrame) -> bool:
    """Convenience wrapper — True iff the bar is swing-tradeable."""
    return evaluate(bars).passed
