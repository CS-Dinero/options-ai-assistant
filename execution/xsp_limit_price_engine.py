"""execution/xsp_limit_price_engine.py — Conservative limit price calculation for XSP spreads."""
from __future__ import annotations

def compute_close_limit(
    short_bid: float,
    short_ask: float,
    long_bid: float,
    long_ask: float,
    urgency: int,
) -> tuple[float, float]:
    """
    Returns (target_limit, max_chase_width) for closing a spread.
    Higher urgency → accept worse price.
    """
    # Mid of the spread net debit (what you pay to close credit spread)
    short_mid = (short_bid + short_ask) / 2
    long_mid  = (long_bid  + long_ask)  / 2
    spread_mid = round(short_mid - long_mid, 4)  # net credit remaining

    # Conservative: start at mid
    # High urgency: accept up to ask
    if urgency >= 90:
        target = round(spread_mid * 0.80, 4)   # accept 20% worse than mid
    elif urgency >= 70:
        target = round(spread_mid * 0.90, 4)
    else:
        target = round(spread_mid * 0.95, 4)   # near mid

    max_chase = round((short_ask - short_bid + long_ask - long_bid) * 0.5, 4)
    return target, max_chase
