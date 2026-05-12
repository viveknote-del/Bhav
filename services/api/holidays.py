"""NSE trading holidays.

⚠️ VERIFY ANNUALLY against the official NSE calendar:
   https://www.nseindia.com/resources/exchange-communication-holidays

Indian holidays move year-to-year — Holi, Good Friday, Eid, Diwali, etc.
are lunar/Christian-calendar driven and shift each year. The list below
is a best-effort estimate for 2026 calendar. If you see the scanner run
on a day NSE was closed, add that date here.

A scan that runs on a holiday is not catastrophic — yfinance returns
empty or stale bars and the scan completes with zero breakouts. But it
wastes Claude tokens on the EOD digest. Better to gate.
"""
from __future__ import annotations

from datetime import date

# Format: ISO date → human label. Sorted for readability.
NSE_HOLIDAYS_2026: dict[date, str] = {
    date(2026, 1, 26):  "Republic Day",
    date(2026, 3, 4):   "Holi",                      # verify
    date(2026, 4, 3):   "Good Friday",               # verify
    date(2026, 4, 14):  "Dr Ambedkar Jayanti",
    date(2026, 5, 1):   "Maharashtra Day",
    date(2026, 8, 17):  "Independence Day (observed)",  # Aug 15 is Sat → observed Mon
    date(2026, 10, 2):  "Mahatma Gandhi Jayanti",
    date(2026, 11, 9):  "Diwali — Laxmi Puja",       # verify; muhurat trading often happens
    date(2026, 12, 25): "Christmas Day",
}


def is_nse_holiday(d: date) -> bool:
    return d in NSE_HOLIDAYS_2026


def holiday_name(d: date) -> str | None:
    return NSE_HOLIDAYS_2026.get(d)
