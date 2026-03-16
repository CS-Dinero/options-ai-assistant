"""
engines/iv_regime.py
IV percentile → regime classification.
"""


def classify_iv_regime(iv_percentile: float) -> str:
    """
    Classify implied volatility environment.

    Returns:
        "cheap"    — IV percentile < 20  (buy premium: calendars, debit spreads)
        "moderate" — 20–44               (balanced)
        "elevated" — 45–69               (lean toward selling premium)
        "rich"     — 70+                 (strong credit spread environment)
    """
    if iv_percentile < 20:
        return "cheap"
    elif iv_percentile < 45:
        return "moderate"
    elif iv_percentile < 70:
        return "elevated"
    return "rich"


def compute_iv_rank(
    current_iv: float,
    iv_52w_low: float,
    iv_52w_high: float,
) -> float | None:
    """
    IV Rank = (current_iv - 52w_low) / (52w_high - 52w_low)

    Returns a value 0.0–1.0:
        0.0 = IV at 52-week low  (buy premium: calendars, diagonals)
        1.0 = IV at 52-week high (sell premium: credit spreads)

    Returns None if inputs are invalid or unavailable.
    Use-cases:
        IVR < 0.20 → strongly favor calendars / diagonals
        IVR > 0.60 → strongly favor credit spreads
        IVR missing → scorer normalizes via reweighting
    """
    try:
        if current_iv is None or iv_52w_low is None or iv_52w_high is None:
            return None
        spread = iv_52w_high - iv_52w_low
        if spread <= 0:
            return None
        rank = (current_iv - iv_52w_low) / spread
        return round(max(0.0, min(1.0, rank)), 4)
    except (TypeError, ZeroDivisionError):
        return None


def classify_iv_rank(iv_rank: float | None) -> str:
    """
    Classify IVR into strategic tiers.
    Returns 'unknown' when iv_rank is None — scorer normalizes gracefully.
    """
    if iv_rank is None:
        return "unknown"
    if iv_rank < 0.20:
        return "very_low"
    elif iv_rank < 0.40:
        return "low"
    elif iv_rank < 0.60:
        return "moderate"
    elif iv_rank < 0.80:
        return "high"
    return "very_high"
