"""
strategies/bear_put_debit.py
Bear put debit spread generator.

Logic:
  - Long put:  nearest ATM put (buy the move)
  - Short put: nearest put to lower EM boundary (cap the cost)
  - Only emit if entry is a net debit
"""

from calculator.chain_helpers import nearest_atm, nearest_strike_to
from calculator.risk_engine    import price_debit_spread, compute_contracts, prob_itm_proxy, prob_touch_proxy
from calculator.trade_scoring  import score_trade


def generate_bear_put_debit_spreads(
    market: dict,
    chain: list[dict],
    derived: dict,
) -> list[dict]:
    """
    Generate bear put debit spread candidates.

    Returns a list of candidate dicts (0 or 1 for MVP).
    """
    results   = []
    lower_em  = derived["lower_em"]
    spot      = market["spot_price"]
    short_dte = market["short_dte_target"]

    long_leg  = nearest_atm(chain, "put", short_dte, spot)
    short_leg = nearest_strike_to(chain, "put", short_dte, lower_em)

    if not long_leg or not short_leg:
        return results
    if short_leg["strike"] >= long_leg["strike"]:
        return results

    actual_width = long_leg["strike"] - short_leg["strike"]
    economics    = price_debit_spread(long_leg["mid"], short_leg["mid"], actual_width)

    if economics["entry_debit_credit"] >= 0:
        return results

    contracts = compute_contracts(
        market["preferred_risk_dollars"],
        economics["max_loss"],
    )

    candidate = {
        "strategy_type":    "bear_put_debit",
        "direction":        "bearish",
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
        "notes": (
            f"Buy {long_leg['strike']:.0f} put / "
            f"Sell {short_leg['strike']:.0f} put near lower EM {lower_em}"
        ),
    }

    candidate["confidence_score"] = score_trade(candidate, market, derived)
    results.append(candidate)
    return results
