"""
engines/term_structure.py
Term structure slope computation and classification.
"""


def compute_term_slope(front_iv: float, back_iv: float) -> float:
    """
    slope = back_month_IV - front_month_IV

    Positive = back month more expensive (contango, normal)
    Negative = front month more expensive (backwardation, stressed)
    """
    return round(back_iv - front_iv, 2)


def classify_term_structure(term_slope: float) -> str:
    """
    Classify the IV term structure.

    Returns:
        "contango"       — slope > +1.0   (calendar/credit-spread friendly)
        "flat"           — slope ±1.0     (neutral)
        "backwardation"  — slope < -1.0   (front vol expensive; debit spreads ok)
    """
    if term_slope > 1.0:
        return "contango"
    elif term_slope < -1.0:
        return "backwardation"
    return "flat"
