"""Unit tests for the consolidation breakout detector."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from services.breakout import consolidation


def make_bars(closes: list[float], volumes: list[int], start: str = "2025-01-01") -> pd.DataFrame:
    idx = pd.bdate_range(start=start, periods=len(closes))
    df = pd.DataFrame({
        "open":   [c for c in closes],
        "high":   [c * 1.005 for c in closes],
        "low":    [c * 0.995 for c in closes],
        "close":  closes,
        "volume": volumes,
    }, index=idx)
    return df


def test_returns_none_when_history_too_short():
    bars = make_bars([100.0] * 30, [1_000_000] * 30)
    assert consolidation.detect("X.NS", bars) is None


def test_returns_none_when_no_breakout():
    bars = make_bars([100.0] * 50, [1_000_000] * 50)        # flat forever
    assert consolidation.detect("X.NS", bars) is None


def test_returns_none_when_range_too_wide():
    # Highly volatile 20 days = not a consolidation
    rng = np.random.default_rng(seed=1)
    closes = (100.0 + rng.normal(0, 10, 50)).tolist() + [120.0]
    vols = [1_000_000] * 51
    assert consolidation.detect("X.NS", make_bars(closes, vols)) is None


def test_returns_none_when_volume_too_low():
    closes = [100.0] * 50 + [102.0]
    vols = [1_000_000] * 50 + [500_000]                      # break on low volume
    assert consolidation.detect("X.NS", make_bars(closes, vols)) is None


def test_clean_consolidation_break_fires():
    # 50 bars tight around 100, then today closes at 103 on heavy volume
    rng = np.random.default_rng(seed=42)
    closes = (100.0 + rng.uniform(-0.5, 0.5, 50)).tolist() + [103.0]
    vols = [1_000_000] * 50 + [2_500_000]

    sig = consolidation.detect("X.NS", make_bars(closes, vols))
    assert sig is not None
    assert sig.breakout_type == "CONSOLIDATION"
    assert sig.breakout_level is not None
    assert sig.price == 103.0
    assert sig.pattern_quality > 0.0
    assert "tightness" in sig.indicators


def test_tighter_consolidation_scores_higher():
    rng = np.random.default_rng(seed=7)
    tight = (100.0 + rng.uniform(-0.3, 0.3, 50)).tolist() + [103.0]
    loose = (100.0 + rng.uniform(-2.0, 2.0, 50)).tolist() + [103.0]
    vols = [1_000_000] * 50 + [2_500_000]

    sig_tight = consolidation.detect("X.NS", make_bars(tight, vols))
    sig_loose = consolidation.detect("X.NS", make_bars(loose, vols))
    assert sig_tight is not None
    if sig_loose is not None:
        assert sig_tight.pattern_quality >= sig_loose.pattern_quality


def test_rejects_close_in_lower_half_of_bar():
    """A bar that tags resistance and rolls over is a textbook failed
    breakout — must close in the upper half of its own range to qualify."""
    rng = np.random.default_rng(seed=42)
    closes = (100.0 + rng.uniform(-0.5, 0.5, 50)).tolist() + [103.0]
    vols = [1_000_000] * 50 + [2_500_000]

    bars = make_bars(closes, vols)
    # Override today's bar: today's high is 105 (well above close), low is 102.9
    # close 103 in a range [102.9, 105] → position = (103-102.9)/(105-102.9) ≈ 0.05
    # i.e. close near the bottom of the bar
    last_idx = bars.index[-1]
    bars.loc[last_idx, "open"] = 104.5
    bars.loc[last_idx, "high"] = 105.0
    bars.loc[last_idx, "low"] = 102.9
    bars.loc[last_idx, "close"] = 103.0

    assert consolidation.detect("X.NS", bars) is None
