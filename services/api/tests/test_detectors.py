"""Unit tests for breakout detectors. Pure functions — no DB, no network."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from services.breakout import fifty_two_week, volume_spike


def make_bars(closes: list[float], volumes: list[int], start: str = "2025-01-01") -> pd.DataFrame:
    """Build a bars DataFrame from price/volume sequences. Open/High/Low
    are synthesised so they're internally consistent."""
    assert len(closes) == len(volumes)
    idx = pd.bdate_range(start=start, periods=len(closes))
    df = pd.DataFrame({
        "open":   [c * 0.99 for c in closes],
        "high":   [c * 1.01 for c in closes],
        "low":    [c * 0.98 for c in closes],
        "close":  closes,
        "volume": volumes,
    }, index=idx)
    return df


# ──────────────────── 52-week high ──────────────────────

class TestFiftyTwoWeekHigh:
    def test_returns_none_when_history_too_short(self):
        bars = make_bars([100.0] * 100, [1_000_000] * 100)
        assert fifty_two_week.detect("X.NS", bars) is None

    def test_returns_none_when_close_equals_prior_high(self):
        # 252 bars at 100, today also 100 — no break
        closes = [100.0] * 252 + [100.0]
        vols = [1_000_000] * 253
        bars = make_bars(closes, vols)
        assert fifty_two_week.detect("X.NS", bars) is None

    def test_returns_none_when_break_below_buffer(self):
        # Prior high 100, today 100.2 (only 0.2% above — under 0.5% buffer)
        closes = [100.0] * 252 + [100.2]
        vols = [1_000_000] * 253
        bars = make_bars(closes, vols)
        assert fifty_two_week.detect("X.NS", bars) is None

    def test_returns_none_when_volume_too_low(self):
        # Clean break but volume is below 1.2× average
        closes = [100.0] * 252 + [105.0]
        vols = [1_000_000] * 252 + [800_000]   # below avg
        bars = make_bars(closes, vols)
        assert fifty_two_week.detect("X.NS", bars) is None

    def test_clear_breakout_fires(self):
        # Noisy ±1% around 100 for 252 days (gives RSI a realistic range
        # of gains and losses to chew on), then today breaks to 105
        # on heavy volume.
        rng = np.random.default_rng(seed=17)
        base = (100.0 + rng.uniform(-1.0, 1.0, 252)).tolist()
        closes = base + [105.0]
        vols = [1_000_000] * 252 + [2_000_000]
        bars = make_bars(closes, vols)
        sig = fifty_two_week.detect("X.NS", bars)
        assert sig is not None
        assert sig.breakout_type == "FIFTY_TWO_WEEK_HIGH"
        assert sig.price == 105.0
        assert sig.volume_ratio == pytest.approx(2.0, rel=1e-3)
        assert sig.indicators["rsi_at_break"] < 75

    def test_returns_none_when_already_overbought(self):
        # Sustained uptrend pushes RSI into >80 territory by the time of
        # the 52w-high break — the "buying tops" pattern that mean-reverts.
        # Generate a long climb so RSI saturates high.
        closes = [50.0 + i * 0.2 for i in range(252)] + [105.0]
        vols = [1_000_000] * 252 + [2_000_000]
        bars = make_bars(closes, vols)
        # Sanity check: should produce a high RSI
        from services.breakout._ta import rsi
        assert rsi(bars, 14) > 75
        # And the detector should now reject it
        assert fifty_two_week.detect("X.NS", bars) is None


# ──────────────────── volume spike ──────────────────────

class TestVolumeSpike:
    def test_returns_none_when_history_too_short(self):
        bars = make_bars([100.0] * 10, [1_000_000] * 10)
        assert volume_spike.detect("X.NS", bars) is None

    def test_returns_none_when_volume_below_3x(self):
        # 2x is below the 3x threshold
        closes = [100.0] * 25 + [101.0]
        vols = [1_000_000] * 25 + [2_000_000]
        bars = make_bars(closes, vols)
        assert volume_spike.detect("X.NS", bars) is None

    def test_returns_none_when_close_below_open(self):
        # Heavy volume but red bar — not a breakout
        closes = [100.0] * 25
        vols = [1_000_000] * 25
        bars = make_bars(closes, vols)
        # Last bar: open 100, close 99 (red), volume 5M
        bars.iloc[-1, bars.columns.get_loc("open")] = 100.0
        bars.iloc[-1, bars.columns.get_loc("close")] = 99.0
        bars.iloc[-1, bars.columns.get_loc("volume")] = 5_000_000
        assert volume_spike.detect("X.NS", bars) is None

    def test_clean_volume_spike_fires(self):
        # 25 bars at avg 1M volume, today 4M, close clearly above open
        closes = [100.0] * 25
        vols = [1_000_000] * 25
        bars = make_bars(closes, vols)
        bars.iloc[-1, bars.columns.get_loc("open")] = 100.0
        bars.iloc[-1, bars.columns.get_loc("close")] = 103.0
        bars.iloc[-1, bars.columns.get_loc("volume")] = 4_000_000

        sig = volume_spike.detect("X.NS", bars)
        assert sig is not None
        assert sig.breakout_type == "VOLUME_SPIKE"
        assert sig.volume_ratio == pytest.approx(4.0, rel=1e-3)
        assert sig.breakout_level is None
