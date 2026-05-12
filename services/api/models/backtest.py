from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class BacktestIn(BaseModel):
    start: date
    end: date
    forward_window_days: int = Field(default=20, ge=1, le=120)
    win_threshold: float = Field(default=0.05, ge=0, le=1)


class DetectorSummary(BaseModel):
    detector: str
    n_signals: int
    hit_rate: float
    win_rate: float
    mean_forward_return: float
    mean_composite_score: float


class BacktestOut(BaseModel):
    start: date
    end: date
    forward_window_days: int
    win_threshold: float
    universe_size: int
    summaries: list[DetectorSummary]
