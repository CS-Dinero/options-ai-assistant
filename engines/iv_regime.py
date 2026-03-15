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
