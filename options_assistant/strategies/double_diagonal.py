"""
strategies/double_diagonal.py
Double diagonal spread generator.

Structure:
  Bull call diagonal (long deep ITM call / short OTM call above upper EM)
  + Bear put diagonal (long deep ITM put  / short OTM put below lower EM)

Combined into one candidate representing both legs of the non-directional structure.

Best VGA: neutral_time_spreads + positive gamma
Entry filter: both diagonals must independently qualify (delta, OI, extrinsic checks)
"""

from __future__ import annotations

from calculator.risk_engine    import compute_contracts, prob_itm_proxy
from calculator.trade_scoring  import score_trade
from engines.gamma_engine      import gamma_trap_distance, spot_position_vs_trap
from config.settings import (
    DIAGONAL_TARGET_MULTIPLIER,
    DIAGONAL_STOP_PERCENT,
    DIAGONAL_LONG_DELTA_MIN, DIAGONAL_LONG_DELTA_MAX,
    DIAGONAL_SHORT_DELTA_MIN, DIAGONAL_SHORT_DELTA_MAX,
    DIAGONAL_MAX_DEBIT_PCT_OF_WIDTH,
    MAX_LONG_EXTRINSIC_RATIO,
    MIN_LONG_LEG_OPEN_INTEREST,
    MAX_BID_ASK_SPREAD_PCT,
)


def _sf(v, default=None):
    try:
        return float(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _extrinsic_ratio(leg: dict, spot: float, opt_type: str) -> float:
    mid    = leg.get("mid", 0)
    strike = leg["strike"]
    if not mid or mid <= 0:
        return 1.0
    intrinsic = max(0.0, spot - strike) if "call" in opt_type else max(0.0, strike - spot)
    return max(0.0, mid - intrinsic) / mid


def _bid_ask_pct(row: dict) -> float:
    mid = row.get("mid", 0)
    if not mid or mid <= 0:
        return 1.0
    return (row.get("ask", 0) - row.get("bid", 0)) / mid


def _find_leg(chain: list[dict], opt_type: str, target_dte: int,
              delta_min: float, delta_max: float,
              spot: float, near_strike: float | None = None,
              oi_min: int = 0, spread_max: float = 1.0,
              extrinsic_max: float = 1.0) -> dict | None:
    rows = [r for r in chain if r.get("option_type") == opt_type]
    if not rows:
        return None
    dtes    = sorted(set(r["dte"] for r in rows))
    best_dte = min(dtes, key=lambda d: abs(d - target_dte))
    pool    = [r for r in rows if r["dte"] == best_dte]

    candidates = []
    for r in pool:
        abs_d = abs(r.get("delta") or 0)
        if not (delta_min <= abs_d <= delta_max):
            continue
        if oi_min and (r.get("open_interest") or 0) < oi_min:
            continue
        sp = _bid_ask_pct(r)
        if r.get("mid", 0) > 0 and sp > spread_max:
            continue
        if extrinsic_max < 1.0 and spot > 0:
            er = _extrinsic_ratio(r, spot, opt_type)
            if er > extrinsic_max:
                continue
        candidates.append(r)

    if not candidates:
        return None
    if near_strike is not None:
        return min(candidates, key=lambda r: abs(r["strike"] - near_strike))
    mid_delta = (delta_min + delta_max) / 2
    return min(candidates, key=lambda r: abs(abs(r.get("delta") or 0) - mid_delta))


def generate_double_diagonal_candidates(
    market: dict,
    chain:  list[dict],
    derived: dict,
) -> list[dict]:
    """
    Generate a double diagonal candidate when both legs qualify.
    Returns 0 or 1 candidate.
    """
    results = []

    # Regime gates — double diagonal needs neutral/positive environment
    iv_r    = derived.get("iv_regime", "")
    term_s  = derived.get("term_structure", "")
    vga     = derived.get("vga_environment", "mixed")

    if (iv_r, term_s) in (("rich", "backwardation"),):
        return results
    if vga in ("trend_directional",):
        return results   # not a time-spread environment
    if iv_r not in ("cheap", "moderate", "elevated"):
        return results

    spot      = market["spot_price"]
    upper_em  = derived["upper_em"]
    lower_em  = derived["lower_em"]
    short_dte = market.get("short_dte_target", 7)
    long_dte  = market.get("long_dte_target", 60)

    # Bull call diagonal leg selection
    long_call  = _find_leg(chain, "call", long_dte,
                           DIAGONAL_LONG_DELTA_MIN, DIAGONAL_LONG_DELTA_MAX,
                           spot, oi_min=MIN_LONG_LEG_OPEN_INTEREST,
                           spread_max=MAX_BID_ASK_SPREAD_PCT,
                           extrinsic_max=MAX_LONG_EXTRINSIC_RATIO)
    short_call = _find_leg(chain, "call", short_dte,
                           DIAGONAL_SHORT_DELTA_MIN, DIAGONAL_SHORT_DELTA_MAX,
                           spot, near_strike=upper_em)

    # Bear put diagonal leg selection
    long_put   = _find_leg(chain, "put", long_dte,
                           DIAGONAL_LONG_DELTA_MIN, DIAGONAL_LONG_DELTA_MAX,
                           spot, oi_min=MIN_LONG_LEG_OPEN_INTEREST,
                           spread_max=MAX_BID_ASK_SPREAD_PCT,
                           extrinsic_max=MAX_LONG_EXTRINSIC_RATIO)
    short_put  = _find_leg(chain, "put", short_dte,
                           DIAGONAL_SHORT_DELTA_MIN, DIAGONAL_SHORT_DELTA_MAX,
                           spot, near_strike=lower_em)

    if not all([long_call, short_call, long_put, short_put]):
        return results

    # Structural sanity
    if short_call["strike"] < long_call["strike"]:
        return results
    if short_put["strike"] > long_put["strike"]:
        return results

    # Pricing — total debit is sum of both diagonal debits
    call_debit = round(long_call["mid"] - short_call["mid"], 2)
    put_debit  = round(long_put["mid"]  - short_put["mid"],  2)
    if call_debit <= 0 or put_debit <= 0:
        return results
    total_debit = round(call_debit + put_debit, 2)

    # Width caps on each side
    call_width = abs(short_call["strike"] - long_call["strike"])
    put_width  = abs(long_put["strike"]   - short_put["strike"])
    if (call_width > 0 and call_debit > call_width * DIAGONAL_MAX_DEBIT_PCT_OF_WIDTH):
        return results
    if (put_width > 0 and put_debit > put_width * DIAGONAL_MAX_DEBIT_PCT_OF_WIDTH):
        return results

    max_loss      = round(total_debit * 100, 2)
    target_exit   = round(total_debit * DIAGONAL_TARGET_MULTIPLIER, 2)
    stop_value    = round(total_debit * (1 - DIAGONAL_STOP_PERCENT), 2)
    contracts     = compute_contracts(market.get("preferred_risk_dollars", 500), max_loss)

    gamma_trap = derived.get("gamma_trap")
    trap_dist  = gamma_trap_distance(spot, gamma_trap)
    spot_vs_t  = spot_position_vs_trap(spot, gamma_trap)

    avg_short_delta = (abs(short_call.get("delta") or 0.25) + abs(short_put.get("delta") or 0.25)) / 2

    notes = (
        f"Double diagonal | call side: ${long_call['strike']:.0f}/${short_call['strike']:.0f} "
        f"| put side: ${short_put['strike']:.0f}/${long_put['strike']:.0f} "
        f"| total debit {total_debit:.2f} | {vga}"
    )

    candidate = {
        "strategy_type":      "double_diagonal",
        "direction":          "neutral_double_diagonal",
        "symbol":             market["symbol"],
        # Use call diagonal as primary representation
        "short_expiration":   short_call["expiration"],
        "long_expiration":    long_call["expiration"],
        "long_strike":        long_call["strike"],
        "short_strike":       short_call["strike"],
        "hedge_strike":       None,
        "width":              round((call_width + put_width) / 2, 2),
        "entry_debit_credit": total_debit,
        "max_profit":         None,
        "max_loss":           max_loss,
        "target_exit_value":  target_exit,
        "stop_value":         stop_value,
        "prob_itm_proxy":     prob_itm_proxy(avg_short_delta),
        "prob_touch_proxy":   min(1.0, 2 * avg_short_delta),
        "contracts":          contracts,
        "confidence_score":   0,
        "notes":              notes,
        "short_dte":          short_call["dte"],
        "long_dte":           long_call["dte"],
        # Diagnostics
        "long_call_strike":   long_call["strike"],
        "short_call_strike":  short_call["strike"],
        "long_put_strike":    long_put["strike"],
        "short_put_strike":   short_put["strike"],
        "call_debit":         call_debit,
        "put_debit":          put_debit,
        "long_delta":         long_call.get("delta"),
        "short_delta":        short_call.get("delta"),
        "long_open_interest": long_call.get("open_interest", 0),
        "gamma_trap_distance": trap_dist,
        "spot_vs_trap":        spot_vs_t,
    }

    candidate["confidence_score"] = score_trade(candidate, market, derived)
    results.append(candidate)
    return results
