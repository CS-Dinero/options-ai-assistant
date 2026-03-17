"""
backtest/utils.py
Shared date/time and chain-lookup helpers for Phase 4 backtesting.
"""

from __future__ import annotations
from datetime import date, timedelta, datetime


def daterange(start: str, end: str):
    """Yield ISO date strings from start to end inclusive."""
    current = datetime.strptime(start, "%Y-%m-%d").date()
    end_dt  = datetime.strptime(end,   "%Y-%m-%d").date()
    while current <= end_dt:
        yield current.strftime("%Y-%m-%d")
        current += timedelta(days=1)


def compute_days_held(entry_date: str, exit_date: str) -> int:
    """Number of calendar days between entry and exit."""
    try:
        entry = datetime.strptime(entry_date, "%Y-%m-%d").date()
        exit_ = datetime.strptime(exit_date,  "%Y-%m-%d").date()
        return max(0, (exit_ - entry).days)
    except (ValueError, TypeError):
        return 0


def get_chain_snapshot_for_date(chain_history: dict, date_str: str) -> list[dict]:
    """
    Return the chain snapshot for a given date.
    Falls back to the nearest available prior date if exact date is missing.
    """
    if date_str in chain_history:
        return chain_history[date_str]

    # Find nearest prior date
    available = sorted(d for d in chain_history.keys() if d <= date_str)
    if available:
        return chain_history[available[-1]]

    return []


def next_trading_date(date_str: str, chain_history: dict) -> str | None:
    """Return the next available date in chain_history after date_str."""
    available = sorted(d for d in chain_history.keys() if d > date_str)
    return available[0] if available else None


def trading_dates_between(start: str, end: str, chain_history: dict) -> list[str]:
    """Return all dates in chain_history between start and end inclusive."""
    return sorted(d for d in chain_history.keys() if start <= d <= end)


def safe_float(value, default: float | None = None) -> float | None:
    """Convert any value to float, returning default on failure."""
    if value in (None, "", "null", "nan", "NaN"):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Convert any value to int, returning default on failure."""
    if value in (None, "", "null"):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
