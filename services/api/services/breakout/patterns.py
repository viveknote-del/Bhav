"""Chart pattern detectors — flag, cup-and-handle, ascending triangle.

These are geometric heuristics, not the result of training. Expect false
positives: a real chart pattern is fuzzy and subjective. The backtest
harness (services/backtest.py) is the truth — tune thresholds against
historical hit rates, not against intuition.

Each subtype detector is a pure function. The top-level `detect` tries
them in order and returns the highest-quality match (or None).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from services.breakout._ta import atr
from services.breakout.types import BreakoutSignal, PatternSubtype


# ──────────────────── FLAG ──────────────────────
# Pole: 5-15 day strong move up (>= 15%). Flag: 5-15 day tight sideways/down
# drift after the pole. Break: today closes above the flag's high.

POLE_MIN_GAIN = 0.15
POLE_LEN_RANGE = (5, 15)
FLAG_LEN_RANGE = (5, 15)
FLAG_MAX_RETRACE = 0.50            # flag must give back < 50% of the pole
FLAG_MAX_RANGE_RATIO = 0.45        # flag range <= 45% of pole range


def detect_flag(symbol: str, bars: pd.DataFrame) -> BreakoutSignal | None:
    if len(bars) < POLE_LEN_RANGE[1] + FLAG_LEN_RANGE[1] + 5:
        return None

    bars = bars.sort_index()
    today = bars.iloc[-1]
    close = bars["close"].values

    best: tuple[BreakoutSignal, float] | None = None

    for flag_len in range(FLAG_LEN_RANGE[0], FLAG_LEN_RANGE[1] + 1):
        for pole_len in range(POLE_LEN_RANGE[0], POLE_LEN_RANGE[1] + 1):
            pole_end = -flag_len - 1
            pole_start = pole_end - pole_len
            if pole_start < -len(bars) + 1:
                continue

            pole = bars.iloc[pole_start:pole_end]
            flag = bars.iloc[pole_end:-1]

            pole_gain = (pole["close"].iloc[-1] - pole["close"].iloc[0]) / pole["close"].iloc[0]
            if pole_gain < POLE_MIN_GAIN:
                continue

            pole_top = float(pole["high"].max())
            pole_bot = float(pole["low"].min())
            flag_top = float(flag["high"].max())
            flag_bot = float(flag["low"].min())

            # Flag must consolidate, not give back too much of the pole
            retrace = (pole_top - flag_bot) / (pole_top - pole_bot or 1e-9)
            if retrace > FLAG_MAX_RETRACE:
                continue

            # Flag range tight relative to the pole range
            pole_range = max(pole_top - pole_bot, 1e-9)
            flag_range = max(flag_top - flag_bot, 1e-9)
            if flag_range / pole_range > FLAG_MAX_RANGE_RATIO:
                continue

            # Today breaks the flag's high
            if today["close"] <= flag_top:
                continue

            tightness = flag_range / pole_range
            quality = max(0.0, 1.0 - tightness / FLAG_MAX_RANGE_RATIO)

            avg_vol_20 = float(bars["volume"].iloc[-21:-1].mean())
            volume_ratio = float(today["volume"]) / max(avg_vol_20, 1.0)

            sig = BreakoutSignal(
                symbol=symbol,
                breakout_type="PATTERN",
                pattern_subtype="FLAG",
                price=float(today["close"]),
                breakout_level=flag_top,
                volume_ratio=volume_ratio,
                pattern_quality=quality,
                indicators={
                    "pole_gain": pole_gain,
                    "pole_len": pole_len,
                    "flag_len": flag_len,
                    "flag_top": flag_top,
                    "retrace_pct": retrace,
                },
            )
            if best is None or quality > best[1]:
                best = (sig, quality)

    return best[0] if best else None


# ──────────────────── CUP AND HANDLE ──────────────────────
# U-shape over 30-90 days followed by a small handle pullback (<12%) and
# break above the cup's rim.

CUP_LEN_RANGE = (30, 90)
CUP_MIN_DEPTH = 0.10               # at least 10% drawdown from rim
CUP_MAX_DEPTH = 0.35
HANDLE_LEN_RANGE = (3, 15)
HANDLE_MAX_DEPTH = 0.12


def detect_cup_handle(symbol: str, bars: pd.DataFrame) -> BreakoutSignal | None:
    if len(bars) < CUP_LEN_RANGE[1] + HANDLE_LEN_RANGE[1] + 5:
        return None

    bars = bars.sort_index()
    today = bars.iloc[-1]

    # Sweep handle and cup lengths; pick the highest-quality match
    best: tuple[BreakoutSignal, float] | None = None

    for handle_len in range(HANDLE_LEN_RANGE[0], HANDLE_LEN_RANGE[1] + 1):
        for cup_len in (40, 60, 80):                # coarse grid; full sweep is slow
            handle_end = -1
            handle_start = -handle_len - 1
            cup_end = handle_start
            cup_start = cup_end - cup_len
            if cup_start < -len(bars) + 1:
                continue

            cup = bars.iloc[cup_start:cup_end]
            handle = bars.iloc[handle_start:handle_end]

            left_rim = float(cup["close"].iloc[0])
            right_rim = float(cup["close"].iloc[-1])
            trough = float(cup["low"].min())

            cup_rim = max(left_rim, right_rim)
            depth = (cup_rim - trough) / cup_rim
            if depth < CUP_MIN_DEPTH or depth > CUP_MAX_DEPTH:
                continue

            # Rims approximately level (within 10%)
            if abs(left_rim - right_rim) / cup_rim > 0.10:
                continue

            handle_top = float(handle["high"].max())
            handle_low = float(handle["low"].min())
            handle_depth = (handle_top - handle_low) / handle_top
            if handle_depth > HANDLE_MAX_DEPTH:
                continue

            # Break above the cup rim
            if today["close"] <= cup_rim * 1.002:
                continue

            # Symmetry: trough roughly in the middle of the cup
            trough_idx = cup["low"].values.argmin()
            symmetry = 1.0 - abs(trough_idx - len(cup) / 2) / (len(cup) / 2)
            quality = max(0.0, min(1.0, symmetry * (1.0 - handle_depth / HANDLE_MAX_DEPTH)))

            avg_vol_20 = float(bars["volume"].iloc[-21:-1].mean())
            volume_ratio = float(today["volume"]) / max(avg_vol_20, 1.0)

            sig = BreakoutSignal(
                symbol=symbol,
                breakout_type="PATTERN",
                pattern_subtype="CUP_HANDLE",
                price=float(today["close"]),
                breakout_level=cup_rim,
                volume_ratio=volume_ratio,
                pattern_quality=quality,
                indicators={
                    "cup_len": cup_len,
                    "cup_depth_pct": depth,
                    "handle_len": handle_len,
                    "handle_depth_pct": handle_depth,
                    "symmetry": symmetry,
                    "cup_rim": cup_rim,
                },
            )
            if best is None or quality > best[1]:
                best = (sig, quality)

    return best[0] if best else None


# ──────────────────── ASCENDING TRIANGLE ──────────────────────
# Flat resistance (>= 3 touches within 2% of each other) + rising support
# (linear regression slope on lows > 0). Break above resistance.

TRIANGLE_WINDOW = 30
RESISTANCE_BAND = 0.02             # 2%
MIN_RESISTANCE_TOUCHES = 3


def detect_triangle(symbol: str, bars: pd.DataFrame) -> BreakoutSignal | None:
    if len(bars) < TRIANGLE_WINDOW + 5:
        return None

    bars = bars.sort_index()
    today = bars.iloc[-1]
    window = bars.iloc[-(TRIANGLE_WINDOW + 1):-1]

    # Find a horizontal-ish resistance: the local max, count bars within 2% of it
    res = float(window["high"].max())
    touches = int((window["high"] >= res * (1 - RESISTANCE_BAND)).sum())
    if touches < MIN_RESISTANCE_TOUCHES:
        return None

    # Lows trending up: linear regression slope > 0 and reasonable strength
    lows = window["low"].values.astype(float)
    x = np.arange(len(lows), dtype=float)
    slope, intercept = np.polyfit(x, lows, 1)
    avg_low = float(lows.mean())
    if slope <= 0:
        return None
    normalised_slope = slope / max(avg_low, 1e-9)
    if normalised_slope < 0.0005:                # at least 0.05% / day rise
        return None

    if today["close"] <= res * 1.003:
        return None

    avg_vol_20 = float(bars["volume"].iloc[-21:-1].mean())
    volume_ratio = float(today["volume"]) / max(avg_vol_20, 1.0)

    quality = min(1.0, (touches - MIN_RESISTANCE_TOUCHES + 1) / 5.0) * min(
        1.0, normalised_slope / 0.005
    )

    return BreakoutSignal(
        symbol=symbol,
        breakout_type="PATTERN",
        pattern_subtype="TRIANGLE",
        price=float(today["close"]),
        breakout_level=res,
        volume_ratio=volume_ratio,
        pattern_quality=quality,
        indicators={
            "resistance": res,
            "touches": touches,
            "lower_slope_normalised": normalised_slope,
            "window": TRIANGLE_WINDOW,
        },
    )


# ──────────────────── DISPATCH ──────────────────────

_PATTERN_DETECTORS = [
    ("FLAG", detect_flag),
    ("CUP_HANDLE", detect_cup_handle),
    ("TRIANGLE", detect_triangle),
]


def detect(symbol: str, bars: pd.DataFrame) -> BreakoutSignal | None:
    """Run all pattern detectors; return the highest-quality match."""
    best: BreakoutSignal | None = None
    for _name, fn in _PATTERN_DETECTORS:
        sig = fn(symbol, bars)
        if sig is None:
            continue
        if best is None or sig.pattern_quality > best.pattern_quality:
            best = sig
    return best
