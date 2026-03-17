"""
strategies/bull_call_debit.py
Bull call debit spread generator.

Logic:
  - Long call:  nearest ATM call (buy the move)
  - Short call: nearest call to upper EM boundary (cap the cost)
  - Only emit if entry is a net debit
"""

from calculator.chain_helpers import nearest_atm, nearest_strike_to
from calculator.risk_engine    import price_debit_spread, compute_contracts, prob_itm_proxy, prob_touch_proxy
from calculator.trade_scoring  import score_trade


def generate_bull_call_debit_spreads(
    market: dict,
    chain: list[dict],
    derived: dict,
) -> list[dict]:
    """
    Generate bull call debit spread candidates.

    Returns a list of candidate dicts (0 or 1 for MVP).
    """
    results   = []
    upper_em  = derived["upper_em"]
    spot      = market["spot_price"]
    short_dte = market["short_dte_target"]

    long_leg  = nearest_atm(chain, "call", short_dte, spot)
    short_leg = nearest_strike_to(chain, "call", short_dte, upper_em)

    if not long_leg or not short_leg:
        return results
    if short_leg["strike"] <= long_leg["strike"]:
        return results

    actual_width = short_leg["strike"] - long_leg["strike"]
    economics    = price_debit_spread(long_leg["mid"], short_leg["mid"], actual_width)

    # Must be a net debit (entry_debit_credit is negative for debit paid)
    if economics["entry_debit_credit"] >= 0:
        return results

    contracts = compute_contracts(
        market["preferred_risk_dollars"],
        economics["max_loss"],
    )

    candidate = {
        "strategy_type":    "bull_call_debit",
        "direction":        "bullish",
        "symbol":           market["symbol"],
        "short_expiration": short_leg["expiration"],
        "long_expiration":  long_leg["expiration"],
        "long_strike":      long_leg["strike"],
        "short_strike":     short_leg["strike"],
        "width":            actual_width,
        "long_delta":       long_leg["delta"],
        "short_delta":      short_leg["delta"],
        "long_iv":          long_leg["iv"],
        **economics,
        "prob_itm_proxy":   prob_itm_proxy(short_leg["delta"]),
        "prob_touch_proxy": prob_touch_proxy(long_leg["delta"]),
        "contracts":        contracts,
        "confidence_score": 0,
        "short_dte":        short_leg["dte"],
        "long_dte":         long_leg["dte"],
        "notes": (
            f"Buy {long_leg['strike']:.0f} call / "
            f"Sell {short_leg['strike']:.0f} call near upper EM {upper_em}"
        ),
    }

    candidate["confidence_score"] = score_trade(candidate, market, derived)
    results.append(candidate)
    return results
