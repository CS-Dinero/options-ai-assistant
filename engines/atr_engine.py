"""
engines/atr_engine.py
ATR trend classification and EM/ATR ratio.
"""


def classify_atr_trend(current_atr: float, prior_atr: float) -> str:
    """
    Classify realized volatility trend.

    Returns:
        "rising"  — ATR increased > 8% period-over-period
        "falling" — ATR decreased > 8%
        "flat"    — within ±8%
    """
    if prior_atr <= 0:
        return "flat"
    change_pct = (current_atr - prior_atr) / prior_atr
    if change_pct > 0.08:
        return "rising"
    elif change_pct < -0.08:
        return "falling"
    return "flat"


def em_atr_ratio(expected_move: float, atr: float) -> float:
    """
    EM / ATR ratio — regime context for strategy suitability.

    Interpretation:
        > 4  : strong range potential → calendars / condors / credit spreads
        2–4  : balanced
        < 2  : breakout risk elevated → debit spreads more viable
    """
    if atr <= 0:
        return 0.0
    return round(expected_move / atr, 2)
