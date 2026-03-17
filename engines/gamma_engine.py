"""
engines/gamma_engine.py
Real Gamma Exposure (GEX) engine.

Formula (institutional standard):
    GEX = gamma * open_interest * 100 * spot_price
    calls = positive (dealer long gamma → pinning)
    puts  = negative (dealer short gamma → acceleration)

Outputs:
    gex_by_strike  — net GEX aggregated per strike
    total_gex      — sum of all signed GEX
    gamma_flip     — strike where cumulative GEX crosses zero
    gamma_trap     — strike with largest positive GEX cluster (pinning magnet)
    gamma_regime   — positive / negative / neutral / unknown

All functions are None-safe. Missing gamma or OI rows are skipped silently.
"""

from __future__ import annotations
from typing import Dict, List, Optional


# ─────────────────────────────────────────────
# PER-ROW GEX
# ─────────────────────────────────────────────

def compute_signed_gex(row: dict, spot_price: float) -> Optional[float]:
    """
    Compute signed GEX for one option contract row.

    Returns None if gamma, OI, or option_type are missing/invalid.
    Callers should skip None results silently.
    """
    gamma       = row.get("gamma")
    oi          = row.get("open_interest")
    option_type = row.get("option_type")

    if gamma is None or oi in (None, 0) or option_type not in ("call", "put"):
        return None

    try:
        raw_gex = float(gamma) * float(oi) * 100.0 * float(spot_price)
    except (TypeError, ValueError):
        return None

    return raw_gex if option_type == "call" else -raw_gex


# ─────────────────────────────────────────────
# CHAIN AGGREGATION
# ─────────────────────────────────────────────

def aggregate_gex_by_strike(
    chain: List[dict],
    spot_price: float,
) -> Dict[float, float]:
    """
    Aggregate signed GEX across all chain rows, keyed by strike.

    Rows with missing gamma or OI are silently skipped.
    Returns a strike-sorted dict: {strike: net_gex}
    """
    gex_by_strike: Dict[float, float] = {}

    for row in chain:
        strike = row.get("strike")
        if strike is None:
            continue

        signed_gex = compute_signed_gex(row, spot_price)
        if signed_gex is None:
            continue

        k = float(strike)
        gex_by_strike[k] = gex_by_strike.get(k, 0.0) + signed_gex

    return dict(sorted(gex_by_strike.items()))


def compute_total_gex(gex_by_strike: Dict[float, float]) -> Optional[float]:
    """
    Sum all net GEX values across strikes.

    Returns None if no data available (triggers scorer normalization).
    Positive → dealers net long gamma → range-bound / mean-reverting.
    Negative → dealers net short gamma → trending / volatile.
    """
    if not gex_by_strike:
        return None
    return sum(gex_by_strike.values())


# ─────────────────────────────────────────────
# GAMMA FLIP
# ─────────────────────────────────────────────

def estimate_gamma_flip(gex_by_strike: Dict[float, float]) -> Optional[float]:
    """
    Estimate the gamma flip level: strike where net GEX crosses zero.

    Uses linear interpolation between adjacent strikes where sign changes.
    The flip level is the regime boundary:
        price above flip → typically positive gamma → range-bound
        price below flip → typically negative gamma → trend-prone

    Returns None if fewer than 2 strikes or no sign change found.
    """
    if len(gex_by_strike) < 2:
        return None

    strikes = sorted(gex_by_strike.keys())

    for i in range(len(strikes) - 1):
        s1, s2 = strikes[i], strikes[i + 1]
        g1, g2 = gex_by_strike[s1], gex_by_strike[s2]

        if g1 == 0:
            return s1

        if g1 * g2 < 0:
            span = g2 - g1
            if span == 0:
                return s1
            frac = abs(g1) / abs(span)
            return round(s1 + frac * (s2 - s1), 2)

    return None


# ─────────────────────────────────────────────
# GAMMA TRAP
# ─────────────────────────────────────────────

def identify_gamma_trap(gex_by_strike: Dict[float, float]) -> Optional[float]:
    """
    Identify the gamma trap: strike with the largest positive GEX.

    The gamma trap is the strike where dealer hedging creates the strongest
    gravitational pull — price tends to pin or return here.

    Returns None if no positive GEX strikes exist.
    """
    if not gex_by_strike:
        return None

    positive = {k: v for k, v in gex_by_strike.items() if v > 0}
    if not positive:
        return None

    return max(positive, key=lambda k: positive[k])


# ─────────────────────────────────────────────
# REGIME CLASSIFIER
# ─────────────────────────────────────────────

def classify_gamma_regime(total_gex: Optional[float]) -> str:
    """
    Classify overall gamma regime from total GEX.

    Returns:
        "positive" — dealers net long gamma → mean-reversion, credit spreads
        "negative" — dealers net short gamma → trending, debit spreads
        "neutral"  — near-zero GEX → balanced
        "unknown"  — no data (scorer normalizes via reweighting)
    """
    if total_gex is None:
        return "unknown"
    if total_gex > 1e6:       # threshold avoids noise near zero
        return "positive"
    if total_gex < -1e6:
        return "negative"
    return "neutral"


# ─────────────────────────────────────────────
# CONVENIENCE: FULL PIPELINE
# ─────────────────────────────────────────────

def compute_gamma_context(chain: list[dict], spot_price: float) -> dict:
    """
    Run the complete GEX pipeline from a chain and spot price.

    Returns a dict with all gamma fields ready to merge into derived context.
    All values are None-safe — missing data produces 'unknown' regime.
    """
    gex_by_strike = aggregate_gex_by_strike(chain, spot_price)
    total_gex     = compute_total_gex(gex_by_strike)
    gamma_flip    = estimate_gamma_flip(gex_by_strike)
    gamma_trap    = identify_gamma_trap(gex_by_strike)
    gamma_regime  = classify_gamma_regime(total_gex)

    return {
        "gex_by_strike": gex_by_strike,
        "total_gex":     total_gex,
        "gamma_flip":    gamma_flip,
        "gamma_trap":    gamma_trap,
        "gamma_regime":  gamma_regime,
    }


# ─────────────────────────────────────────────
# GAMMA TRAP TARGETING HELPERS
# ─────────────────────────────────────────────

def is_gamma_trap_near_spot(
    spot_price: float,
    gamma_trap: Optional[float],
    expected_move: float,
    proximity_pct: float = 0.5,
) -> bool:
    """
    Return True if gamma trap is within proximity_pct * EM of spot.

    The default 0.5 EM proximity means: only use the gamma trap as a
    calendar strike when it's within half the expected move of spot.
    Beyond that, the trap is too far away to aid short-term pinning.

    Example:
        spot=520, EM=9, trap=522 → distance=2, threshold=4.5 → True (use trap)
        spot=520, EM=9, trap=535 → distance=15, threshold=4.5 → False (use ATM)
    """
    if gamma_trap is None or expected_move <= 0:
        return False
    return abs(gamma_trap - spot_price) <= proximity_pct * expected_move


def gamma_trap_distance(
    spot_price: float,
    gamma_trap: Optional[float],
) -> Optional[float]:
    """
    Signed distance from spot to gamma trap.
    Positive = trap above spot (bullish lean).
    Negative = trap below spot (bearish lean).
    None = trap unavailable.
    """
    if gamma_trap is None:
        return None
    return round(gamma_trap - spot_price, 2)


def spot_position_vs_trap(
    spot_price: float,
    gamma_trap: Optional[float],
) -> str:
    """
    Classify spot position relative to gamma trap.

    Returns:
        "above_trap"  — spot > trap (price broken through, directional)
        "at_trap"     — spot within $2 of trap (pinned)
        "below_trap"  — spot < trap (bearish lean)
        "unknown"     — no trap data
    """
    if gamma_trap is None:
        return "unknown"
    dist = spot_price - gamma_trap
    if abs(dist) <= 2.0:
        return "at_trap"
    elif dist > 0:
        return "above_trap"
    return "below_trap"
