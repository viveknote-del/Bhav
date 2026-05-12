"""Unit tests for market_hours utilities."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from market_hours import IST, is_market_open, is_trading_day, is_weekend


class TestIsTradingDay:
    def test_weekday_non_holiday_is_trading(self):
        assert is_trading_day(date(2026, 5, 13)) is True       # Wednesday

    def test_saturday_is_not_trading(self):
        assert is_trading_day(date(2026, 5, 16)) is False      # Saturday
        assert is_weekend(date(2026, 5, 16)) is True

    def test_sunday_is_not_trading(self):
        assert is_trading_day(date(2026, 5, 17)) is False      # Sunday

    def test_known_holiday_is_not_trading(self):
        assert is_trading_day(date(2026, 1, 26)) is False      # Republic Day
        assert is_trading_day(date(2026, 12, 25)) is False     # Christmas

    def test_independence_day_observed_monday(self):
        # 2026-08-15 is a Saturday, so it's a non-trading weekend regardless.
        # The Aug-17 observed entry in the holiday list covers the Monday.
        assert is_trading_day(date(2026, 8, 15)) is False
        assert is_trading_day(date(2026, 8, 17)) is False


class TestIsMarketOpen:
    def test_during_session_on_trading_day(self):
        at = datetime(2026, 5, 13, 11, 30, tzinfo=IST)         # 11:30 IST Wed
        assert is_market_open(at) is True

    def test_at_open_boundary(self):
        at = datetime(2026, 5, 13, 9, 15, tzinfo=IST)
        assert is_market_open(at) is True

    def test_at_close_boundary(self):
        at = datetime(2026, 5, 13, 15, 30, tzinfo=IST)
        assert is_market_open(at) is True

    def test_before_open_is_closed(self):
        at = datetime(2026, 5, 13, 9, 0, tzinfo=IST)
        assert is_market_open(at) is False

    def test_after_close_is_closed(self):
        at = datetime(2026, 5, 13, 16, 0, tzinfo=IST)
        assert is_market_open(at) is False

    def test_on_weekend_is_closed(self):
        at = datetime(2026, 5, 16, 11, 30, tzinfo=IST)         # Sat at 11:30
        assert is_market_open(at) is False

    def test_on_holiday_is_closed(self):
        at = datetime(2026, 1, 26, 11, 30, tzinfo=IST)         # Republic Day
        assert is_market_open(at) is False

    def test_converts_utc_to_ist(self):
        # 11:00 UTC on Wed = 16:30 IST → market closed
        utc = datetime(2026, 5, 13, 11, 0, tzinfo=ZoneInfo("UTC"))
        assert is_market_open(utc) is False

        # 06:00 UTC on Wed = 11:30 IST → market open
        utc_open = datetime(2026, 5, 13, 6, 0, tzinfo=ZoneInfo("UTC"))
        assert is_market_open(utc_open) is True
