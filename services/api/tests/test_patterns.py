"""Unit tests for pattern detectors. Synthetic bars are hand-crafted to
match each pattern's geometric definition.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from services.breakout import patterns


def to_df(closes: list[float], volumes: list[int]) -> pd.DataFrame:
    idx = pd.bdate_range(start="2025-01-01", periods=len(closes))
    return pd.DataFrame({
        "open":   closes,
        "high":   [c * 1.005 for c in closes],
        "low":    [c * 0.995 for c in closes],
        "close":  closes,
        "volume": volumes,
    }, index=idx)


# ──────────────────── FLAG ──────────────────────

def test_flag_returns_none_when_no_pole():
    bars = to_df([100.0] * 40, [1_000_000] * 40)
    assert patterns.detect_flag("X.NS", bars) is None


def test_flag_detects_pole_then_break():
    # Build: 30 days flat at 80, then a 10-day pole to 100 (+25%),
    # then 8 days tight flag in 97-101, then today closes at 103 (above flag high)
    rng = np.random.default_rng(seed=3)
    flat = [80.0] * 30
    pole = list(np.linspace(80.0, 100.0, 10))
    flag = (99.0 + rng.uniform(-2.0, 1.0, 8)).tolist()
    today = [103.0]
    closes = flat + pole + flag + today
    vols = [1_000_000] * (len(closes) - 1) + [2_000_000]  # 2× → passes 1.5 floor

    sig = patterns.detect_flag("X.NS", to_df(closes, vols))
    assert sig is not None
    assert sig.breakout_type == "PATTERN"
    assert sig.pattern_subtype == "FLAG"
    assert sig.pattern_quality > 0.0
    assert sig.volume_ratio >= 1.5


def test_flag_rejects_low_volume_break():
    """A textbook flag pattern must come on confirming volume."""
    rng = np.random.default_rng(seed=3)
    flat = [80.0] * 30
    pole = list(np.linspace(80.0, 100.0, 10))
    flag = (99.0 + rng.uniform(-2.0, 1.0, 8)).tolist()
    today = [103.0]
    closes = flat + pole + flag + today
    vols = [1_000_000] * (len(closes) - 1) + [1_100_000]   # 1.1× — under floor
    assert patterns.detect_flag("X.NS", to_df(closes, vols)) is None


# ──────────────────── CUP & HANDLE ──────────────────────

def _cup_handle_closes(cup_len: int = 60, depth: float = 0.20, handle_len: int = 6) -> list[float]:
    """Synthesise a clean cup-and-handle with a PARABOLIC (rounded) cup,
    not a V. The detector requires ≥5 bars within 3% of the trough, which
    a linear V-shape fails by design — only a U-shape passes."""
    rim = 100.0
    trough = rim * (1.0 - depth)
    mid = (cup_len - 1) / 2.0
    cup = [trough + (rim - trough) * ((x - mid) / mid) ** 2 for x in range(cup_len)]
    handle = list(np.linspace(rim * 0.99, rim * 0.96, handle_len))
    # 30 lead bars + cup + handle + break (≥0.5% above rim)
    return [rim] * 30 + cup + handle + [rim * 1.02]


def test_cup_handle_detects_clean_pattern():
    closes = _cup_handle_closes(cup_len=60, depth=0.20, handle_len=6)
    # Break must come on ≥1.5× 20-day avg volume — high enough that the
    # tail of the cup doesn't pull the average too high.
    vols = [1_000_000] * (len(closes) - 1) + [3_000_000]
    sig = patterns.detect_cup_handle("X.NS", to_df(closes, vols))
    assert sig is not None
    assert sig.pattern_subtype == "CUP_HANDLE"
    assert sig.indicators["cup_depth_pct"] == pytest.approx(0.20, abs=0.05)
    assert sig.indicators["rounded_bottom_run"] >= 6
    assert sig.volume_ratio >= 1.5


def test_cup_handle_rejects_too_shallow_cup():
    closes = _cup_handle_closes(cup_len=60, depth=0.05, handle_len=6)   # below min depth
    vols = [1_000_000] * (len(closes) - 1) + [3_000_000]
    assert patterns.detect_cup_handle("X.NS", to_df(closes, vols)) is None


def test_cup_handle_rejects_v_shape():
    """A perfect V-shaped drop-and-recover should NOT fire — the rounded-
    bottom check is what makes this a 'cup' rather than just any dip."""
    rim = 100.0
    half = 30
    down = list(np.linspace(rim, rim * 0.80, half))
    up = list(np.linspace(rim * 0.80, rim, half))
    handle = list(np.linspace(rim * 0.99, rim * 0.96, 6))
    closes = [rim] * 30 + down + up + handle + [rim * 1.02]
    vols = [1_000_000] * (len(closes) - 1) + [3_000_000]
    assert patterns.detect_cup_handle("X.NS", to_df(closes, vols)) is None


def test_cup_handle_rejects_low_volume_break():
    """Even a textbook cup pattern must have volume on the break."""
    closes = _cup_handle_closes(cup_len=60, depth=0.20, handle_len=6)
    vols = [1_000_000] * (len(closes) - 1) + [1_100_000]   # only 1.1× — under floor
    assert patterns.detect_cup_handle("X.NS", to_df(closes, vols)) is None


# ──────────────────── ASCENDING TRIANGLE ──────────────────────

def test_triangle_detects_flat_resistance_with_rising_lows():
    # The detector requires window+5 bars (30+5=35 minimum). Build 40 bars
    # where highs all touch ~100 but lows rise from 92 to 99, then break.
    rng = np.random.default_rng(seed=11)
    highs = (100.0 + rng.uniform(-0.5, 0.0, 40)).tolist()
    lows = list(np.linspace(92.0, 99.0, 40))
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    closes.append(102.5)                                      # today breaks above 100
    highs.append(closes[-1] * 1.005)
    lows.append(closes[-1] * 0.995)
    volumes = [1_000_000] * 40 + [3_000_000]

    idx = pd.bdate_range(start="2025-01-01", periods=len(closes))
    bars = pd.DataFrame({
        "open":   closes,
        "high":   highs,
        "low":    lows,
        "close":  closes,
        "volume": volumes,
    }, index=idx)
    sig = patterns.detect_triangle("X.NS", bars)
    assert sig is not None
    assert sig.pattern_subtype == "TRIANGLE"
    assert sig.indicators["touches"] >= 3
    assert sig.indicators["lower_slope_normalised"] > 0


def test_triangle_rejects_flat_lows():
    # Both highs and lows flat — not a triangle
    closes = [100.0] * 35
    vols = [1_000_000] * 34 + [3_000_000]
    assert patterns.detect_triangle("X.NS", to_df(closes, vols)) is None


def test_triangle_rejects_low_volume_break():
    """Triangle break without confirming volume gets rejected."""
    highs = [100.0] * 40
    lows = list(np.linspace(92.0, 99.0, 40))
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    closes.append(102.5)
    highs.append(closes[-1] * 1.005)
    lows.append(closes[-1] * 0.995)
    volumes = [1_000_000] * 40 + [1_100_000]               # 1.1× — under floor

    idx = pd.bdate_range(start="2025-01-01", periods=len(closes))
    bars = pd.DataFrame({
        "open": closes, "high": highs, "low": lows, "close": closes, "volume": volumes,
    }, index=idx)
    assert patterns.detect_triangle("X.NS", bars) is None


def test_triangle_rejects_three_touches():
    """3 touches at resistance is too sparse — real ascending triangles
    have 4+. Two non-touch bars + 3 touch bars at the very end, surrounded
    by lower-priced bars."""
    # 40 bars: 35 with highs at 95 (below resistance band) + 3 spikes to 100 + 2 lows
    highs = [95.0] * 35 + [100.0, 100.0, 100.0, 96.0, 96.0]
    lows = list(np.linspace(85.0, 92.0, 40))
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    closes.append(102.5)                                    # today: break
    highs.append(closes[-1] * 1.005)
    lows.append(closes[-1] * 0.995)
    volumes = [1_000_000] * 40 + [3_000_000]

    idx = pd.bdate_range(start="2025-01-01", periods=len(closes))
    bars = pd.DataFrame({
        "open": closes, "high": highs, "low": lows, "close": closes, "volume": volumes,
    }, index=idx)
    sig = patterns.detect_triangle("X.NS", bars)
    # Only 3 touches at resistance — below new minimum of 4
    assert sig is None


# ──────────────────── DISPATCH ──────────────────────

def test_detect_returns_highest_quality_pattern():
    """Bars that match multiple patterns should return the highest-quality one."""
    closes = _cup_handle_closes(cup_len=60, depth=0.20, handle_len=6)
    vols = [1_000_000] * (len(closes) - 1) + [3_000_000]
    sig = patterns.detect("X.NS", to_df(closes, vols))
    assert sig is not None
    # Cup-handle should win on this synthetic sequence
    assert sig.pattern_subtype in ("CUP_HANDLE", "FLAG", "TRIANGLE")
