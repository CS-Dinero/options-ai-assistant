"""
engines/skew_engine.py
25-delta put/call IV skew computation and classification.
"""

from typing import Optional


def compute_skew(put_25d_iv: Optional[float], call_25d_iv: Optional[float]) -> Optional[float]:
    """
    skew = put_25d_IV - call_25d_IV

    Positive = puts more expensive (normal market behavior, fear premium)
    High positive = strong downside demand

    Returns None if either input is missing.
    """
    if put_25d_iv is None or call_25d_iv is None:
        return None
    return round(put_25d_iv - call_25d_iv, 2)


def classify_skew(skew_value: Optional[float]) -> str:
    """
    Classify skew level.

    Returns:
        "high_put_skew" — skew > 5    (downside protection expensive)
        "normal_skew"   — skew 2–5   (typical market behavior)
        "flat_skew"     — skew < 2   (balanced or call-rich environment)
        "unknown"       — skew is None (missing inputs)
    """
    if skew_value is None:
        return "unknown"
    if skew_value > 5:
        return "high_put_skew"
    elif skew_value >= 2:
        return "normal_skew"
    return "flat_skew"
