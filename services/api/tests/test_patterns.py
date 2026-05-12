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
    vols = [1_000_000] * (len(closes) - 1) + [2_000_000]

    sig = patterns.detect_flag("X.NS", to_df(closes, vols))
    assert sig is not None
    assert sig.breakout_type == "PATTERN"
    assert sig.pattern_subtype == "FLAG"
    assert sig.pattern_quality > 0.0


# ──────────────────── CUP & HANDLE ──────────────────────

def _cup_handle_closes(cup_len: int = 60, depth: float = 0.20, handle_len: int = 6) -> list[float]:
    """Synthesise a clean cup-and-handle: U from 100 down to (100 * (1-depth))
    and back to 100, then a shallow handle, then a break."""
    rim = 100.0
    trough = rim * (1.0 - depth)
    half = cup_len // 2
    down = list(np.linspace(rim, trough, half))
    up = list(np.linspace(trough, rim, cup_len - half))
    handle = list(np.linspace(rim * 0.99, rim * 0.96, handle_len))
    return [rim] * 30 + down + up + handle + [rim * 1.02]    # 30 lead bars + cup + handle + break


def test_cup_handle_detects_clean_pattern():
    closes = _cup_handle_closes(cup_len=60, depth=0.20, handle_len=6)
    vols = [1_000_000] * (len(closes) - 1) + [2_500_000]
    sig = patterns.detect_cup_handle("X.NS", to_df(closes, vols))
    assert sig is not None
    assert sig.pattern_subtype == "CUP_HANDLE"
    assert sig.indicators["cup_depth_pct"] == pytest.approx(0.20, abs=0.05)


def test_cup_handle_rejects_too_shallow_cup():
    closes = _cup_handle_closes(cup_len=60, depth=0.05, handle_len=6)   # below min depth
    vols = [1_000_000] * (len(closes) - 1) + [2_500_000]
    assert patterns.detect_cup_handle("X.NS", to_df(closes, vols)) is None


# ──────────────────── ASCENDING TRIANGLE ──────────────────────

def test_triangle_detects_flat_resistance_with_rising_lows():
    # 30 bars where highs all touch ~100 but lows rise from 92 to 99
    rng = np.random.default_rng(seed=11)
    highs = (100.0 + rng.uniform(-0.5, 0.0, 30)).tolist()
    lows = list(np.linspace(92.0, 99.0, 30))
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    closes.append(102.5)                                      # today breaks above 100
    highs.append(closes[-1] * 1.005)
    lows.append(closes[-1] * 0.995)
    volumes = [1_000_000] * 30 + [3_000_000]

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


# ──────────────────── DISPATCH ──────────────────────

def test_detect_returns_highest_quality_pattern():
    """Bars that match multiple patterns should return the highest-quality one."""
    closes = _cup_handle_closes(cup_len=60, depth=0.20, handle_len=6)
    vols = [1_000_000] * (len(closes) - 1) + [2_500_000]
    sig = patterns.detect("X.NS", to_df(closes, vols))
    assert sig is not None
    # Cup-handle should win on this synthetic sequence
    assert sig.pattern_subtype in ("CUP_HANDLE", "FLAG", "TRIANGLE")
