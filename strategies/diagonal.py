"""
strategies/diagonal.py
Bull call diagonal and bear put diagonal generator.

80/30-style delta targeting with three hard rejection filters:
  1. Long leg liquidity: OI >= MIN_LONG_LEG_OPEN_INTEREST
  2. Long leg spread: (ask-bid)/mid <= MAX_BID_ASK_SPREAD_PCT
  3. Debit cap: debit <= width * DIAGONAL_MAX_DEBIT_PCT_OF_WIDTH (75% rule)

Regime requirements:
  - IV cheap or moderate
  - Not (rich + backwardation) together

MVP scope: bull call diagonal + bear put diagonal.
Later: double diagonals, event diagonals, roll logic.
"""

from calculator.chain_helpers import filter_chain, nearest_strike_to
from calculator.risk_engine    import compute_contracts, prob_itm_proxy, prob_touch_proxy
from calculator.trade_scoring  import score_trade
from engines.gamma_engine      import gamma_trap_distance, spot_position_vs_trap
from config.settings import (
    DIAGONAL_TARGET_MULTIPLIER,
    DIAGONAL_STOP_PERCENT,
    DIAGONAL_LONG_DELTA_MIN,
    DIAGONAL_LONG_DELTA_MAX,
    DIAGONAL_SHORT_DELTA_MIN,
    DIAGONAL_SHORT_DELTA_MAX,
    DIAGONAL_MAX_DEBIT_PCT_OF_WIDTH,
    MAX_LONG_EXTRINSIC_RATIO,
    MIN_LONG_LEG_OPEN_INTEREST,
    MAX_BID_ASK_SPREAD_PCT,
)

# Reject this IV + term structure combination
_REJECT_COMBOS = {("rich", "backwardation")}


def _bid_ask_spread_pct(row: dict) -> float:
    """(ask - bid) / mid — measures execution cost as % of mid price."""
    mid = row.get("mid", 0)
    if not mid or mid <= 0:
        return 1.0   # treat unknown as worst case
    return round((row.get("ask", 0) - row.get("bid", 0)) / mid, 4)


def _extrinsic_ratio(long_leg: dict, spot_price: float, direction: str) -> float:
    """
    Compute what fraction of the long leg's premium is extrinsic (time value).

    For LEAPS diagonals, this is the real acceptance guard:
        60-70% intrinsic = healthy structure (extrinsic_ratio <= 0.40)
        90%+ extrinsic   = overpaying for time value (reject)

    Formula:
        for call: intrinsic = max(0, spot - strike)
        for put:  intrinsic = max(0, strike - spot)
        extrinsic = mid - intrinsic
        ratio = extrinsic / mid
    """
    mid    = long_leg.get("mid", 0)
    strike = long_leg["strike"]
    if mid <= 0:
        return 1.0  # treat zero-mid as worst case

    if "call" in direction:
        intrinsic = max(0.0, spot_price - strike)
    else:
        intrinsic = max(0.0, strike - spot_price)

    extrinsic = max(0.0, mid - intrinsic)
    return round(extrinsic / mid, 4)


def _find_long_leg(
    chain: list[dict],
    option_type: str,
    long_dte: int,
    spot_price: float = 0.0,
    direction: str = "bull_call_diagonal",
) -> dict | None:
    """
    Find the best long leg:
      - DTE closest to long_dte_target
      - delta magnitude in [DIAGONAL_LONG_DELTA_MIN, DIAGONAL_LONG_DELTA_MAX]
      - OI >= MIN_LONG_LEG_OPEN_INTEREST
      - bid/ask spread pct <= MAX_BID_ASK_SPREAD_PCT
      - extrinsic ratio <= MAX_LONG_EXTRINSIC_RATIO (LEAPS quality filter)
    Among all qualifying, pick the one whose delta is closest to midpoint (0.775).
    """
    rows = [r for r in chain if r["option_type"] == option_type]
    if not rows:
        return None

    dtes     = sorted(set(r["dte"] for r in rows))
    best_dte = min(dtes, key=lambda d: abs(d - long_dte))
    dte_rows = [r for r in rows if r["dte"] == best_dte]

    delta_mid = (DIAGONAL_LONG_DELTA_MIN + DIAGONAL_LONG_DELTA_MAX) / 2

    candidates = []
    for r in dte_rows:
        abs_delta = abs(r.get("delta") or 0)
        if not (DIAGONAL_LONG_DELTA_MIN <= abs_delta <= DIAGONAL_LONG_DELTA_MAX):
            continue
        if (r.get("open_interest") or 0) < MIN_LONG_LEG_OPEN_INTEREST:
            continue
        spread_p = _bid_ask_spread_pct(r)
        if r.get("mid", 0) > 0 and spread_p > MAX_BID_ASK_SPREAD_PCT:
            continue
        # Extrinsic filter: reject if paying too much time value on long leg
        if spot_price > 0:
            ext_ratio = _extrinsic_ratio(r, spot_price, direction)
            if ext_ratio > MAX_LONG_EXTRINSIC_RATIO:
                continue
        candidates.append(r)

    if not candidates:
        return None

    return min(candidates, key=lambda r: abs(abs(r.get("delta") or 0) - delta_mid))


def _find_short_leg(
    chain: list[dict],
    option_type: str,
    short_dte: int,
    em_boundary: float,
) -> dict | None:
    """
    Find the best short leg:
      - DTE closest to short_dte_target
      - strike nearest to em_boundary
      - delta magnitude in [DIAGONAL_SHORT_DELTA_MIN, DIAGONAL_SHORT_DELTA_MAX]
    Falls back to nearest-to-boundary if no delta filter match.
    """
    rows = [r for r in chain if r["option_type"] == option_type]
    if not rows:
        return None

    dtes     = sorted(set(r["dte"] for r in rows))
    best_dte = min(dtes, key=lambda d: abs(d - short_dte))
    dte_rows = [r for r in rows if r["dte"] == best_dte]

    # Primary: delta filter + nearest to EM
    delta_candidates = [
        r for r in dte_rows
        if DIAGONAL_SHORT_DELTA_MIN <= abs(r.get("delta") or 0) <= DIAGONAL_SHORT_DELTA_MAX
    ]

    pool = delta_candidates if delta_candidates else dte_rows
    if not pool:
        return None

    return min(pool, key=lambda r: abs(r["strike"] - em_boundary))


def _regime_ok(iv_regime: str, term_structure: str) -> bool:
    """Reject rich IV + backwardation combination."""
    if (iv_regime, term_structure) in _REJECT_COMBOS:
        return False
    if iv_regime not in ("cheap", "moderate", "elevated"):
        return False
    return True


def _build_diagonal_candidate(
    market: dict,
    derived: dict,
    long_leg: dict,
    short_leg: dict,
    direction: str,
) -> dict | None:
    """Build and validate a diagonal candidate dict."""
    # Structural sanity
    if direction == "bull_call_diagonal":
        if short_leg["strike"] < long_leg["strike"]:
            return None
    else:
        if short_leg["strike"] > long_leg["strike"]:
            return None

    width = round(abs(short_leg["strike"] - long_leg["strike"]), 2)
    debit = round(long_leg["mid"] - short_leg["mid"], 2)

    if debit <= 0:
        return None

    # Debit cap:
    # For short-dated diagonals (long DTE <= 30): use strict debit-pct-of-width check.
    # For LEAPS long legs (long DTE > 30): debit includes substantial intrinsic value
    # and naturally runs 85-97% of width. Skip width-ratio check; use budget check only.
    long_dte_val = long_leg.get("dte", 0)
    if width > 0 and long_dte_val <= 30:
        if debit > width * DIAGONAL_MAX_DEBIT_PCT_OF_WIDTH:
            return None
    # For LEAPS, reject only if debit exceeds the full strike width (clearly wrong pricing)
    elif width > 0 and debit >= width:
        return None

    debit_pct_of_width = round(debit / width, 4) if width > 0 else None
    max_loss           = round(debit * 100, 2)
    target_exit        = round(debit * DIAGONAL_TARGET_MULTIPLIER, 2)
    stop_value         = round(debit * (1 - DIAGONAL_STOP_PERCENT), 2)

    contracts = compute_contracts(
        market.get("preferred_risk_dollars", 500),
        max_loss,
    )

    long_delta  = long_leg.get("delta")
    short_delta = short_leg.get("delta")
    spread_pct  = _bid_ask_spread_pct(long_leg)
    spot        = market["spot_price"]

    # Gamma trap diagnostics for scoring and display
    gamma_trap      = derived.get("gamma_trap")
    trap_dist       = gamma_trap_distance(spot, gamma_trap)
    spot_vs_trap    = spot_position_vs_trap(spot, gamma_trap)
    ext_ratio       = _extrinsic_ratio(long_leg, spot, direction)

    notes = (
        f"{direction.replace('_', ' ').title()} — "
        f"long Δ={abs(long_delta):.2f} OI={long_leg.get('open_interest',0):,} "
        f"spread={spread_pct:.1%}, "
        f"short Δ={abs(short_delta):.2f} near EM boundary, "
        f"debit {debit_pct_of_width:.0%} of width, "
        f"extrinsic {ext_ratio:.0%}, "
        f"spot {spot_vs_trap.replace('_',' ')}"
        if long_delta and short_delta and debit_pct_of_width
        else f"{direction.replace('_', ' ').title()}"
    )

    candidate = {
        "strategy_type":      "diagonal",
        "direction":          direction,
        "symbol":             market["symbol"],
        "short_expiration":   short_leg["expiration"],
        "long_expiration":    long_leg["expiration"],
        "long_strike":        long_leg["strike"],
        "short_strike":       short_leg["strike"],
        "hedge_strike":       None,
        "width":              width,
        "entry_debit_credit": debit,
        "max_profit":         None,
        "max_loss":           max_loss,
        "target_exit_value":  target_exit,
        "stop_value":         stop_value,
        "prob_itm_proxy":     prob_itm_proxy(short_delta or 0.25),
        "prob_touch_proxy":   min(1.0, 2 * abs(short_delta or 0.25)),
        "contracts":          contracts,
        "confidence_score":   0,
        "notes":              notes,
        # Diagnostic fields
        "long_delta":               long_delta,
        "short_delta":              short_delta,
        "long_theta":               long_leg.get("theta"),
        "short_theta":              short_leg.get("theta"),
        "long_vega":                long_leg.get("vega"),
        "short_vega":               short_leg.get("vega"),
        "long_open_interest":       long_leg.get("open_interest", 0),
        "long_bid_ask_spread_pct":  spread_pct,
        "debit_pct_of_width":       debit_pct_of_width,
        "long_extrinsic_ratio":     ext_ratio,
        "gamma_trap_distance":      trap_dist,
        "spot_vs_trap":             spot_vs_trap,
        "short_dte":                short_leg["dte"],
        "long_dte":                 long_leg["dte"],
    }

    return candidate


def generate_diagonal_candidates(
    market: dict,
    chain: list[dict],
    derived: dict,
) -> list[dict]:
    """
    Generate bull call diagonal and bear put diagonal candidates.
    Returns a list of 0–2 candidates.
    """
    results      = []
    iv_regime    = derived.get("iv_regime", "moderate")
    term_struct  = derived.get("term_structure", "flat")

    if not _regime_ok(iv_regime, term_struct):
        return results

    upper_em  = derived["upper_em"]
    lower_em  = derived["lower_em"]
    short_dte = market.get("short_dte_target", 7)
    long_dte  = market.get("long_dte_target", 60)
    spot      = market["spot_price"]

    # ── Bull call diagonal ────────────────────────────────────────────────────
    long_call  = _find_long_leg(chain, "call", long_dte, spot, "bull_call_diagonal")
    short_call = _find_short_leg(chain, "call", short_dte, upper_em)

    if long_call and short_call:
        candidate = _build_diagonal_candidate(
            market, derived, long_call, short_call, "bull_call_diagonal"
        )
        if candidate:
            candidate["confidence_score"] = score_trade(candidate, market, derived)
            results.append(candidate)

    # ── Bear put diagonal ─────────────────────────────────────────────────────
    long_put  = _find_long_leg(chain, "put", long_dte, spot, "bear_put_diagonal")
    short_put = _find_short_leg(chain, "put", short_dte, lower_em)

    if long_put and short_put:
        candidate = _build_diagonal_candidate(
            market, derived, long_put, short_put, "bear_put_diagonal"
        )
        if candidate:
            candidate["confidence_score"] = score_trade(candidate, market, derived)
            results.append(candidate)

    return results
