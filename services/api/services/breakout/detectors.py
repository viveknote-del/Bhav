"""Registry of detector functions. The scan engine iterates this list per symbol.

Add a detector by importing it here and appending its `detect` function.
Each detector is a pure function: `(symbol, bars) -> Optional[BreakoutSignal]`.

Production detectors (positive expectancy in backtest):
- fifty_two_week  +0.24% mean fwd, 28.6% win   (after RSI<75 cap)
- volume_spike    +0.57% mean fwd, 36.4% win
- patterns        +3.60% mean fwd, 37.5% win   ← strongest

Disabled (negative expectancy in 6-month NIFTY 50 backtest):
- consolidation   -1.86% mean fwd, 23.5% win   (even after good-close filter)
  Code is preserved for analysis and possible future re-enable. To re-enable,
  import + append `consolidation.detect` below.
"""
from __future__ import annotations

from services.breakout import (
    fifty_two_week,
    patterns,
    volume_spike,
    # consolidation,                                  # disabled — see note above
)

DETECTORS = [
    fifty_two_week.detect,
    # consolidation.detect,                           # disabled — see note above
    volume_spike.detect,
    patterns.detect,
]
