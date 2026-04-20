"""
engines/expected_move.py
Compute expected move (EM) from ATM straddle or IV formula.
Straddle method is preferred when ATM option prices are available.
"""

import math
from typing import Optional


def compute_expected_move_from_straddle(atm_call_mid: float, atm_put_mid: float) -> float:
    """
    Market-native EM: cost of ATM straddle ≈ 1 SD expected move.
    Most accurate for weekly options where IV is priced in.
    """
    return round(atm_call_mid + atm_put_mid, 2)


def compute_expected_move_from_iv(spot: float, iv_percent: float, dte: int) -> float:
    """
    IV-formula fallback:  EM = S * σ * sqrt(DTE/365)
    Use when ATM straddle prices are unavailable.
    """
    sigma = iv_percent / 100.0
    return round(spot * sigma * math.sqrt(dte / 365.0), 2)


def compute_expected_move(
    spot: float,
    atm_call_mid: Optional[float],
    atm_put_mid: Optional[float],
    iv_percent: float,
    dte: int,
) -> dict:
    """
    Primary:  straddle method if both ATM prices are available.
    Fallback: IV formula.

    Returns:
        expected_move  — 1 SD move estimate
        upper_em       — spot + EM
        lower_em       — spot - EM
        method         — which method was used
    """
    if atm_call_mid and atm_put_mid:
        em     = compute_expected_move_from_straddle(atm_call_mid, atm_put_mid)
        method = "straddle"
    else:
        em     = compute_expected_move_from_iv(spot, iv_percent, dte)
        method = "iv_formula"

    return {
        "expected_move": em,
        "upper_em":      round(spot + em, 2),
        "lower_em":      round(spot - em, 2),
        "method":        method,
    }
