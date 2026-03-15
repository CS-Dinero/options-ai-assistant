"""
strategies/bear_call.py
Bear call credit spread generator.

Logic:
  - Short call: first call ABOVE upper EM with delta 0.10–0.20
  - Long call:  short_strike + spread_width
  - Only emit if entry credit > 0
"""

from calculator.chain_helpers import first_strike_outside_em_with_delta, nearest_strike_to
from calculator.risk_engine    import price_credit_spread, compute_contracts, prob_itm_proxy, prob_touch_proxy
from calculator.trade_scoring  import score_trade
from config.settings           import CREDIT_DELTA_MIN, CREDIT_DELTA_MAX


def generate_bear_call_spreads(
    market: dict,
    chain: list[dict],
    derived: dict,
) -> list[dict]:
    """
    Generate bear call credit spread candidates.

    Returns a list of candidate dicts (0 or 1 for MVP).
    Each candidate is ready for scoring and ranking.
    """
    results   = []
    upper_em  = derived["upper_em"]
    width     = market["default_spread_width"]
    short_dte = market["short_dte_target"]

    # Short leg: first call beyond upper EM within delta filter
    short_leg = first_strike_outside_em_with_delta(
        chain, "call", short_dte, upper_em, CREDIT_DELTA_MIN, CREDIT_DELTA_MAX, "above"
    )
    if not short_leg:
        return results

    # Long leg: hedge at short_strike + width
    long_leg = nearest_strike_to(chain, "call", short_dte, short_leg["strike"] + width)
    if not long_leg or long_leg["strike"] <= short_leg["strike"]:
        return results

    actual_width = long_leg["strike"] - short_leg["strike"]
    economics    = price_credit_spread(short_leg["mid"], long_leg["mid"], actual_width)

    # Must receive a net credit — discard if spread costs money
    if economics["entry_debit_credit"] <= 0:
        return results

    contracts = compute_contracts(
        market["preferred_risk_dollars"],
        economics["max_loss"],
    )

    candidate = {
        "strategy_type":    "bear_call",
        "direction":        "bearish",
        "symbol":           market["symbol"],
        "short_expiration": short_leg["expiration"],
        "long_expiration":  long_leg["expiration"],
        "short_strike":     short_leg["strike"],
        "hedge_strike":     long_leg["strike"],
        "width":            actual_width,
        "short_delta":      short_leg["delta"],
        "hedge_delta":      long_leg["delta"],
        "short_iv":         short_leg["iv"],
        **economics,
        "prob_itm_proxy":   prob_itm_proxy(short_leg["delta"]),
        "prob_touch_proxy": prob_touch_proxy(short_leg["delta"]),
        "contracts":        contracts,
        "confidence_score": 0,
        "notes": (
            f"Short call {short_leg['strike']:.0f} Δ={short_leg['delta']:.2f} "
            f"above upper EM {upper_em}"
        ),
    }

    candidate["confidence_score"] = score_trade(candidate, market, derived)
    results.append(candidate)
    return results
