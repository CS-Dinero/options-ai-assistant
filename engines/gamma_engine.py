"""
engines/gamma_engine.py
GEX (Gamma Exposure) regime classification.

MVP: classify from pre-computed total_gex value.
Phase 2: compute full GEX surface from option chain data.
"""

from typing import Optional


def classify_gamma_regime(total_gex: Optional[float]) -> str:
    """
    Classify dealer gamma positioning from total signed GEX.

    Positive GEX: dealers are net long gamma.
        - Dealers buy dips / sell rips to delta-hedge.
        - Market tends toward mean-reversion and range compression.
        - Favors credit spreads, iron condors, calendars.

    Negative GEX: dealers are net short gamma.
        - Dealers must chase moves to delta-hedge.
        - Market tends toward amplified directional moves.
        - Favors debit spreads and directional structures.

    Returns:
        "positive" — total_gex > +1B
        "negative" — total_gex < -1B
        "neutral"  — within ±1B
        "unknown"  — total_gex is None (triggers score normalization)
    """
    if total_gex is None:
        return "unknown"
    if total_gex > 1e9:
        return "positive"
    elif total_gex < -1e9:
        return "negative"
    return "neutral"


# ─────────────────────────────────────────────
# Phase 2 stubs — chain-based GEX calculation
# These are not used in MVP but define the interface
# for when you want to compute GEX from live chain data.
# ─────────────────────────────────────────────

def compute_signed_gex(
    spot: float,
    gamma: float,
    open_interest: int,
    option_type: str,
) -> float:
    """
    GEX contribution for a single option contract.

    GEX_call = +gamma * OI * 100 * spot
    GEX_put  = -gamma * OI * 100 * spot
    """
    sign = 1 if option_type == "call" else -1
    return sign * gamma * open_interest * 100 * spot


def aggregate_gex_by_strike(chain: list[dict], spot: float) -> dict:
    """
    Sum signed GEX at each strike.
    Returns: {strike: net_gex_value}
    """
    gex_map: dict[float, float] = {}
    for row in chain:
        k   = row["strike"]
        gex = compute_signed_gex(spot, row["gamma"], row["open_interest"], row["option_type"])
        gex_map[k] = gex_map.get(k, 0.0) + gex
    return dict(sorted(gex_map.items()))


def estimate_gamma_flip(gex_by_strike: dict) -> Optional[float]:
    """
    Estimate gamma flip level: strike where cumulative GEX crosses zero.
    Returns the strike closest to the zero crossing.
    """
    strikes = sorted(gex_by_strike.keys())
    cumulative = 0.0
    for strike in strikes:
        prev = cumulative
        cumulative += gex_by_strike[strike]
        if prev < 0 < cumulative or prev > 0 > cumulative:
            return strike
    return None


def identify_gamma_trap(gex_by_strike: dict) -> Optional[float]:
    """
    Gamma trap: strike with the largest absolute GEX concentration.
    Price tends to pin or gravity-pull toward this strike.
    """
    if not gex_by_strike:
        return None
    return max(gex_by_strike, key=lambda k: abs(gex_by_strike[k]))
