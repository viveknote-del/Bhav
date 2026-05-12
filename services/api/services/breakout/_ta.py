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


def sma(bars: pd.DataFrame, window: int) -> float:
    """Simple moving average of close over the last `window` bars."""
    if len(bars) < window:
        return 0.0
    return float(bars["close"].iloc[-window:].mean())


def rsi(bars: pd.DataFrame, window: int = 14) -> float:
    """Wilder's RSI(14) for the last bar. Returns 50.0 (neutral) if there
    isn't enough history."""
    if len(bars) < window + 1:
        return 50.0
    closes = bars["close"]
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder smoothing = EWM with alpha = 1/window (no adjust)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False).mean()
    last_gain = float(avg_gain.iloc[-1])
    last_loss = float(avg_loss.iloc[-1])
    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return 100.0 - 100.0 / (1.0 + rs)


def adx(bars: pd.DataFrame, window: int = 14) -> float:
    """Wilder's ADX(14) — measures trend STRENGTH (not direction).
    > 25 conventionally means "trending"; < 20 means "ranging/choppy".
    Returns 0.0 if there isn't enough history (need ≥ 2*window+1 bars)."""
    if len(bars) < 2 * window + 1:
        return 0.0
    high = bars["high"]
    low = bars["low"]
    close = bars["close"]

    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    alpha = 1.0 / window
    atr_rma = tr.ewm(alpha=alpha, adjust=False).mean().replace(0, 1e-9)
    plus_di = 100.0 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_rma
    minus_di = 100.0 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / atr_rma
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-9)
    adx_series = dx.ewm(alpha=alpha, adjust=False).mean()
    return float(adx_series.iloc[-1])
