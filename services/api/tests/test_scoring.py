"""Unit tests for the composite scoring function."""
from __future__ import annotations

import pandas as pd
import pytest

from services.breakout.scoring import WEIGHTS, score
from services.breakout.types import BreakoutSignal


def make_bars(closes: list[float], volumes: list[int]) -> pd.DataFrame:
    idx = pd.bdate_range(start="2025-01-01", periods=len(closes))
    df = pd.DataFrame({
        "open":   [c * 0.99 for c in closes],
        "high":   [c * 1.01 for c in closes],
        "low":    [c * 0.98 for c in closes],
        "close":  closes,
        "volume": volumes,
    }, index=idx)
    return df


def test_weights_sum_to_1():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_score_in_valid_range():
    bars = make_bars([100.0] * 250 + [110.0], [1_000_000] * 250 + [3_000_000])
    sig = BreakoutSignal(
        symbol="X.NS",
        breakout_type="FIFTY_TWO_WEEK_HIGH",
        price=110.0,
        breakout_level=100.0,
        volume_ratio=3.0,
    )
    s = score(sig, bars)
    assert 0.0 <= s <= 100.0


def test_higher_volume_ratio_increases_score():
    bars = make_bars([100.0] * 250 + [110.0], [1_000_000] * 250 + [3_000_000])
    sig_low = BreakoutSignal("X.NS", "FIFTY_TWO_WEEK_HIGH", 110.0, 100.0, 1.5)
    sig_high = BreakoutSignal("X.NS", "FIFTY_TWO_WEEK_HIGH", 110.0, 100.0, 6.0)
    assert score(sig_high, bars) > score(sig_low, bars)


def test_trend_aligned_break_scores_higher_than_below_ma():
    rising = [100.0 + i * 0.1 for i in range(250)] + [130.0]
    falling = [200.0 - i * 0.2 for i in range(250)] + [165.0]
    vols = [1_000_000] * 250 + [3_000_000]

    bars_up = make_bars(rising, vols)
    bars_down = make_bars(falling, vols)

    sig_up = BreakoutSignal("X.NS", "FIFTY_TWO_WEEK_HIGH", 130.0, 125.0, 3.0)
    sig_down = BreakoutSignal("Y.NS", "FIFTY_TWO_WEEK_HIGH", 165.0, 160.0, 3.0)

    assert score(sig_up, bars_up) > score(sig_down, bars_down)


def test_pattern_quality_increases_score():
    bars = make_bars([100.0] * 250 + [110.0], [1_000_000] * 250 + [3_000_000])
    sig_zero = BreakoutSignal("X.NS", "PATTERN", 110.0, None, 3.0,
                              pattern_subtype="FLAG", pattern_quality=0.0)
    sig_full = BreakoutSignal("X.NS", "PATTERN", 110.0, None, 3.0,
                              pattern_subtype="FLAG", pattern_quality=1.0)
    s_zero = score(sig_zero, bars)
    s_full = score(sig_full, bars)
    assert s_full - s_zero == pytest.approx(WEIGHTS["pattern_quality"] * 100, abs=0.01)
