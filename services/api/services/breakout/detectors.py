"""Registry of detector functions. The scan engine iterates this list per symbol.

Add a detector by importing it here and appending its `detect` function.
Each detector is a pure function: `(symbol, bars) -> Optional[BreakoutSignal]`.
"""
from __future__ import annotations

from services.breakout import (
    consolidation,
    fifty_two_week,
    patterns,
    volume_spike,
)

DETECTORS = [
    fifty_two_week.detect,
    consolidation.detect,
    volume_spike.detect,
    patterns.detect,
]
