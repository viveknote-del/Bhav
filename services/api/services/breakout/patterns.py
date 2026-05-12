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
# Pole: 5-15 day strong move up (>= 18%). Flag: 5-15 day tight sideways/down
# drift after the pole. Break: today closes above the flag's high on volume.

POLE_MIN_GAIN = 0.18                  # was 0.15 — 15% is too easy on volatile names
POLE_LEN_RANGE = (5, 15)
FLAG_LEN_RANGE = (5, 15)
FLAG_MAX_RETRACE = 0.50               # flag must give back < 50% of the pole
FLAG_MAX_RANGE_RATIO = 0.40           # was 0.45 — tighter flag
FLAG_BREAK_BUFFER = 0.005             # NEW: break flag high by ≥ 0.5%
FLAG_VOLUME_FLOOR_RATIO = 1.5         # NEW: today's vol ≥ 1.5× 20d avg


def detect_flag(symbol: str, bars: pd.DataFrame) -> BreakoutSignal | None:
    if len(bars) < POLE_LEN_RANGE[1] + FLAG_LEN_RANGE[1] + 5:
        return None

    bars = bars.sort_index()
    today = bars.iloc[-1]

    # Volume gate first — fastest reject.
    avg_vol_20 = float(bars["volume"].iloc[-21:-1].mean())
    if avg_vol_20 <= 0:
        return None
    volume_ratio = float(today["volume"]) / avg_vol_20
    if volume_ratio < FLAG_VOLUME_FLOOR_RATIO:
        return None

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

            # Today breaks the flag's high with conviction
            if today["close"] <= flag_top * (1 + FLAG_BREAK_BUFFER):
                continue

            tightness = flag_range / pole_range
            quality = max(0.0, 1.0 - tightness / FLAG_MAX_RANGE_RATIO)

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
# U-shape over 40-80 days followed by a small handle pullback, then a
# break above the cup's rim ON VOLUME. The volume confirmation is what
# distinguishes a real cup-handle from any chart that happens to curve.

CUP_LENS = (40, 60, 80)            # try these cup lengths only
CUP_MIN_DEPTH = 0.15               # was 0.10 — too generous
CUP_MAX_DEPTH = 0.35
HANDLE_LEN_RANGE = (3, 12)         # was (3, 15)
HANDLE_MAX_DEPTH = 0.10            # was 0.12 — tighter handle
RIM_TOLERANCE = 0.04               # was 0.10 — rims within 4%
BREAK_BUFFER = 0.005               # was 0.002 — break by ≥ 0.5%
VOLUME_FLOOR_RATIO = 1.5           # NEW: today's vol must be ≥ 1.5× 20d avg
ROUNDED_BOTTOM_BAND = 0.01         # NEW: lows within 1% of trough
ROUNDED_BOTTOM_MIN_RUN = 6         # NEW: ≥ 6 CONSECUTIVE bars in that band


def detect_cup_handle(symbol: str, bars: pd.DataFrame) -> BreakoutSignal | None:
    if len(bars) < max(CUP_LENS) + HANDLE_LEN_RANGE[1] + 5:
        return None

    bars = bars.sort_index()
    today = bars.iloc[-1]

    # Volume gate first — fastest reject path. A "cup-handle" without
    # confirming volume on the break is almost always a false positive.
    avg_vol_20 = float(bars["volume"].iloc[-21:-1].mean())
    if avg_vol_20 <= 0:
        return None
    volume_ratio = float(today["volume"]) / avg_vol_20
    if volume_ratio < VOLUME_FLOOR_RATIO:
        return None

    best: tuple[BreakoutSignal, float] | None = None

    for handle_len in range(HANDLE_LEN_RANGE[0], HANDLE_LEN_RANGE[1] + 1):
        for cup_len in CUP_LENS:
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

            # Rims approximately level (within 4%)
            if abs(left_rim - right_rim) / cup_rim > RIM_TOLERANCE:
                continue

            # Rounded bottom: real cups have a flat-ish region at the low.
            # A V-shape passes a count-based check (the descent and ascent
            # both have bars near the trough by accident) — but it FAILS a
            # *consecutive run* check, because V's only contiguous bars in
            # a tight band span 3-4 indices. A parabolic U gets 10+ in row.
            near_trough_band = trough * (1.0 + ROUNDED_BOTTOM_BAND)
            best_run = 0
            current_run = 0
            for low in cup["low"].values:
                if float(low) <= near_trough_band:
                    current_run += 1
                    if current_run > best_run:
                        best_run = current_run
                else:
                    current_run = 0
            if best_run < ROUNDED_BOTTOM_MIN_RUN:
                continue

            handle_top = float(handle["high"].max())
            handle_low = float(handle["low"].min())
            handle_depth = (handle_top - handle_low) / handle_top
            if handle_depth > HANDLE_MAX_DEPTH:
                continue

            # Break above the cup rim with conviction
            if today["close"] <= cup_rim * (1 + BREAK_BUFFER):
                continue

            # Symmetry: trough roughly in the middle of the cup (within 25%
            # of midpoint — stricter than before)
            trough_idx = int(cup["low"].values.argmin())
            half = len(cup) / 2.0
            symmetry_dist = abs(trough_idx - half) / half
            if symmetry_dist > 0.5:
                continue
            symmetry = 1.0 - symmetry_dist

            quality = max(0.0, min(1.0, symmetry * (1.0 - handle_depth / HANDLE_MAX_DEPTH)))

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
                    "rounded_bottom_run": best_run,
                    "cup_rim": cup_rim,
                    "avg_vol_20": avg_vol_20,
                },
            )
            if best is None or quality > best[1]:
                best = (sig, quality)

    return best[0] if best else None


# ──────────────────── ASCENDING TRIANGLE ──────────────────────
# Flat resistance (>= 4 touches within 1.5% of each other) + rising support
# (linear regression slope on lows > 0). Break above resistance on volume.

TRIANGLE_WINDOW = 30
RESISTANCE_BAND = 0.015                # was 0.02 — 1.5%
MIN_RESISTANCE_TOUCHES = 4             # was 3 — 3 highs near a level is noise
TRIANGLE_BREAK_BUFFER = 0.005          # was 0.003 (the bare 1.003)
TRIANGLE_VOLUME_FLOOR_RATIO = 1.5      # NEW
TRIANGLE_MIN_NORMALISED_SLOPE = 0.001  # was 0.0005 — at least 0.1%/day low rise


def detect_triangle(symbol: str, bars: pd.DataFrame) -> BreakoutSignal | None:
    if len(bars) < TRIANGLE_WINDOW + 5:
        return None

    bars = bars.sort_index()
    today = bars.iloc[-1]
    window = bars.iloc[-(TRIANGLE_WINDOW + 1):-1]

    # Volume gate first.
    avg_vol_20 = float(bars["volume"].iloc[-21:-1].mean())
    if avg_vol_20 <= 0:
        return None
    volume_ratio = float(today["volume"]) / avg_vol_20
    if volume_ratio < TRIANGLE_VOLUME_FLOOR_RATIO:
        return None

    # Flat-ish resistance: count bars within RESISTANCE_BAND of the local max
    res = float(window["high"].max())
    touches = int((window["high"] >= res * (1 - RESISTANCE_BAND)).sum())
    if touches < MIN_RESISTANCE_TOUCHES:
        return None

    # Lows trending up: linear regression slope > 0 and reasonable strength
    lows = window["low"].values.astype(float)
    x = np.arange(len(lows), dtype=float)
    slope, _ = np.polyfit(x, lows, 1)
    avg_low = float(lows.mean())
    if slope <= 0:
        return None
    normalised_slope = slope / max(avg_low, 1e-9)
    if normalised_slope < TRIANGLE_MIN_NORMALISED_SLOPE:
        return None

    # Break above resistance with conviction
    if today["close"] <= res * (1 + TRIANGLE_BREAK_BUFFER):
        return None

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
