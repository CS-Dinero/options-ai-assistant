"""
calculator/chain_helpers.py
Option chain filtering and strike selection utilities.
All strategy generators depend on these helpers.
"""

from typing import Optional


def filter_chain(chain: list[dict], option_type: str, dte: int) -> list[dict]:
    """Return all options of a given type and DTE, sorted by strike ascending."""
    rows = [r for r in chain if r["option_type"] == option_type and r["dte"] == dte]
    return sorted(rows, key=lambda x: x["strike"])


def nearest_atm(
    chain: list[dict],
    option_type: str,
    dte: int,
    spot: float,
) -> Optional[dict]:
    """Return the strike closest to spot for a given type and DTE."""
    rows = filter_chain(chain, option_type, dte)
    if not rows:
        return None
    return min(rows, key=lambda x: abs(x["strike"] - spot))


def nearest_strike_to(
    chain: list[dict],
    option_type: str,
    dte: int,
    target_strike: float,
) -> Optional[dict]:
    """Return the option row whose strike is closest to target_strike."""
    rows = filter_chain(chain, option_type, dte)
    if not rows:
        return None
    return min(rows, key=lambda x: abs(x["strike"] - target_strike))


def first_strike_outside_em_with_delta(
    chain: list[dict],
    option_type: str,
    dte: int,
    em_boundary: float,
    delta_min: float,
    delta_max: float,
    direction: str,         # "above" (for calls) or "below" (for puts)
) -> Optional[dict]:
    """
    For credit spreads: find the first strike beyond the EM boundary
    whose |delta| falls within [delta_min, delta_max].

    If no strike satisfies the delta filter, fall back to the
    first available strike beyond the EM boundary.

    Args:
        em_boundary — upper_em for calls, lower_em for puts
        direction   — "above" searches strikes > boundary
                      "below" searches strikes < boundary
    """
    rows = filter_chain(chain, option_type, dte)

    if direction == "above":
        candidates = [r for r in rows if r["strike"] > em_boundary]
        candidates.sort(key=lambda x: x["strike"])
    else:
        candidates = [r for r in rows if r["strike"] < em_boundary]
        candidates.sort(key=lambda x: x["strike"], reverse=True)

    # Primary: satisfy delta filter
    for row in candidates:
        abs_delta = abs(row["delta"])
        if delta_min <= abs_delta <= delta_max:
            return row

    # Fallback: first candidate beyond EM regardless of delta
    return candidates[0] if candidates else None


def find_option(
    chain: list[dict],
    expiration: str,
    option_type: str,
    strike: float,
) -> Optional[dict]:
    """Exact lookup: find an option by expiration, type, and strike."""
    for row in chain:
        if (
            row["expiration"] == expiration
            and row["option_type"] == option_type
            and row["strike"] == strike
        ):
            return row
    return None
