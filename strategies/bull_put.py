"""
strategies/bull_put.py
Bull put credit spread generator.

Logic:
  - Short put: first put BELOW lower EM with |delta| 0.10–0.20
  - Long put:  short_strike - spread_width
  - Only emit if entry credit > 0
"""

from calculator.chain_helpers import first_strike_outside_em_with_delta, nearest_strike_to
from calculator.risk_engine    import price_credit_spread, compute_contracts, prob_itm_proxy, prob_touch_proxy
from calculator.trade_scoring  import score_trade
from config.settings           import CREDIT_DELTA_MIN, CREDIT_DELTA_MAX


def generate_bull_put_spreads(
    market: dict,
    chain: list[dict],
    derived: dict,
) -> list[dict]:
    """
    Generate bull put credit spread candidates.

    Returns a list of candidate dicts (0 or 1 for MVP).
    """
    results   = []
    lower_em  = derived["lower_em"]
    width     = market["default_spread_width"]
    short_dte = market["short_dte_target"]

    # Short leg: first put below lower EM within delta filter
    short_leg = first_strike_outside_em_with_delta(
        chain, "put", short_dte, lower_em, CREDIT_DELTA_MIN, CREDIT_DELTA_MAX, "below"
    )
    if not short_leg:
        return results

    # Long leg: hedge at short_strike - width
    long_leg = nearest_strike_to(chain, "put", short_dte, short_leg["strike"] - width)
    if not long_leg or long_leg["strike"] >= short_leg["strike"]:
        return results

    actual_width = short_leg["strike"] - long_leg["strike"]
    economics    = price_credit_spread(short_leg["mid"], long_leg["mid"], actual_width)

    if economics["entry_debit_credit"] <= 0:
        return results

    contracts = compute_contracts(
        market["preferred_risk_dollars"],
        economics["max_loss"],
    )

    candidate = {
        "strategy_type":    "bull_put",
        "direction":        "bullish",
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
            f"Short put {short_leg['strike']:.0f} Δ={short_leg['delta']:.2f} "
            f"below lower EM {lower_em}"
        ),
    }

    candidate["confidence_score"] = score_trade(candidate, market, derived)
    results.append(candidate)
    return results
