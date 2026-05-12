"""NSE/BSE market-hours utilities.

All times are Indian Standard Time (Asia/Kolkata; UTC+5:30, no DST).
Both the EOD-scan cron and the intraday loop ask this module before
running so we don't waste API calls on weekends, holidays, or off-hours.

Equity continuous session: 09:15 – 15:30 IST.
Pre-open and post-close auctions are excluded — we want bars from the
live session only.
"""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from holidays import is_nse_holiday

IST = ZoneInfo("Asia/Kolkata")

MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
EOD_SCAN_TIME = time(15, 35)        # 5 min after close, when bars stabilize


def now_ist() -> datetime:
    return datetime.now(IST)


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5          # 5 = Sat, 6 = Sun


def is_trading_day(d: date) -> bool:
    """True if the NSE was open for trading on `d` (weekday, not a holiday)."""
    if is_weekend(d):
        return False
    if is_nse_holiday(d):
        return False
    return True


def is_market_open(at: datetime | None = None) -> bool:
    """True if the equity continuous session is live right now (or `at`).

    Caller must use a timezone-aware datetime; we'll convert to IST.
    """
    at_ist = (at or now_ist()).astimezone(IST)
    if not is_trading_day(at_ist.date()):
        return False
    t = at_ist.time()
    return MARKET_OPEN <= t <= MARKET_CLOSE
