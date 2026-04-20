"""
strategies/calendar.py
ATM / gamma-trap call calendar spread generator.

Entry requirements:
  - IV regime: cheap or moderate only
  - Term structure: contango only (MVP)
  - Strike: gamma trap if available, else nearest ATM
  - Short leg theta >= CALENDAR_THETA_RATIO_MIN * long leg theta
  - Positive net debit

MVP scope: call calendars only.
Later: put calendars, event calendars, double calendars.
"""

from calculator.chain_helpers  import nearest_atm, nearest_strike_to, filter_chain
from calculator.risk_engine     import compute_contracts, prob_itm_proxy, prob_touch_proxy
from calculator.trade_scoring   import score_trade
from engines.gamma_engine       import is_gamma_trap_near_spot
from config.settings import (
    CALENDAR_TARGET_MULTIPLIER,
    CALENDAR_STOP_PERCENT,
    CALENDAR_THETA_RATIO_MIN,
    CALENDAR_IV_REGIMES_OK,
    CALENDAR_TERM_STRUCTURES_OK,
    GAMMA_TRAP_PROXIMITY_PCT,
)


def _find_nearest_dte(chain: list[dict], option_type: str, target_dte: int) -> dict | None:
    """Find the option row whose DTE is closest to target_dte."""
    rows = [r for r in chain if r["option_type"] == option_type]
    if not rows:
        return None
    dtes      = sorted(set(r["dte"] for r in rows))
    best_dte  = min(dtes, key=lambda d: abs(d - target_dte))
    dte_rows  = [r for r in rows if r["dte"] == best_dte]
    return dte_rows[0] if dte_rows else None


def _theta_ratio_ok(short_theta: float | None, long_theta: float | None) -> bool:
    """
    Verify short leg decays at least CALENDAR_THETA_RATIO_MIN faster than long leg.
    Returns True if data is unavailable (skip filter when Greeks missing).
    """
    if short_theta is None or long_theta is None:
        return True   # can't reject what we can't measure
    if long_theta == 0:
        return True
    return abs(short_theta) >= CALENDAR_THETA_RATIO_MIN * abs(long_theta)


def generate_calendar_candidates(
    market: dict,
    chain: list[dict],
    derived: dict,
) -> list[dict]:
    """
    Generate ATM call calendar candidates.

    Returns a list of 0 or 1 candidate dicts.
    """
    results = []

    # ── Regime filters ────────────────────────────────────────────────────────
    if derived.get("iv_regime") not in CALENDAR_IV_REGIMES_OK:
        return results   # IV too rich for calendar

    if derived.get("term_structure") not in CALENDAR_TERM_STRUCTURES_OK:
        return results   # backwardation kills calendar edge

    # ── Strike selection — proximity-aware gamma trap targeting ───────────────
    spot         = market["spot_price"]
    gamma_trap   = derived.get("gamma_trap") or market.get("gamma_trap_strike")
    short_dte_t  = market.get("short_dte_target", 7)
    long_dte_t   = market.get("long_dte_target", 60)
    expected_move = derived.get("expected_move", 9.0)

    # Use gamma trap only when it's close enough to spot to aid pinning
    trap_is_near = is_gamma_trap_near_spot(
        spot, gamma_trap, expected_move, GAMMA_TRAP_PROXIMITY_PCT
    )
    if trap_is_near and gamma_trap:
        calendar_strike = gamma_trap
        trap_label = f"gamma trap ${gamma_trap:.0f}"
    else:
        calendar_strike = spot
        if gamma_trap:
            trap_label = f"ATM (gamma trap ${gamma_trap:.0f} too far)"
        else:
            trap_label = "ATM (no gamma trap data)"

    # Find the short and long leg rows at the chosen strike
    # Short leg: nearest DTE to short_dte_target
    short_candidates = [
        r for r in chain
        if r["option_type"] == "call"
        and abs(r["strike"] - calendar_strike) <= 5   # within $5 of target
    ]
    if not short_candidates:
        return results

    short_dtes = sorted(set(r["dte"] for r in short_candidates))
    best_short_dte = min(short_dtes, key=lambda d: abs(d - short_dte_t))
    long_dtes  = [d for d in sorted(set(r["dte"] for r in chain)) if d > best_short_dte]
    if not long_dtes:
        return results
    best_long_dte = min(long_dtes, key=lambda d: abs(d - long_dte_t))

    # Find the actual option rows
    def best_row(dte: int, strike_target: float) -> dict | None:
        rows = [r for r in chain if r["option_type"] == "call" and r["dte"] == dte]
        if not rows:
            return None
        return min(rows, key=lambda r: abs(r["strike"] - strike_target))

    short_leg = best_row(best_short_dte, calendar_strike)
    long_leg  = best_row(best_long_dte, calendar_strike)

    if not short_leg or not long_leg:
        return results

    # Use same strike for both legs (calendar)
    actual_strike = short_leg["strike"]

    # Re-find long leg at exact same strike if possible
    exact_long = next(
        (r for r in chain
         if r["option_type"] == "call"
         and r["dte"] == best_long_dte
         and r["strike"] == actual_strike),
        long_leg,
    )

    # ── Theta ratio check ─────────────────────────────────────────────────────
    if not _theta_ratio_ok(short_leg.get("theta"), exact_long.get("theta")):
        return results

    # ── Pricing ───────────────────────────────────────────────────────────────
    debit = round(exact_long["mid"] - short_leg["mid"], 2)
    if debit <= 0:
        return results

    max_loss       = round(debit * 100, 2)
    target_exit    = round(debit * CALENDAR_TARGET_MULTIPLIER, 2)
    stop_value     = round(debit * (1 - CALENDAR_STOP_PERCENT), 2)

    contracts = compute_contracts(
        market.get("preferred_risk_dollars", 500),
        max_loss,
    )

    # ── Notes ─────────────────────────────────────────────────────────────────
    theta_note = (
        f"theta ratio {abs(short_leg['theta']):.3f}/{abs(exact_long['theta']):.3f}"
        if short_leg.get("theta") and exact_long.get("theta") else "theta N/A"
    )
    notes = (
        f"Call calendar centered at {trap_label}, strike ${actual_strike:.0f}, "
        f"{derived.get('term_structure','?')} term structure, "
        f"{theta_note}"
    )

    candidate = {
        "strategy_type":      "calendar",
        "direction":          "neutral_call_calendar",
        "symbol":             market["symbol"],
        "short_expiration":   short_leg["expiration"],
        "long_expiration":    exact_long["expiration"],
        "long_strike":        actual_strike,
        "short_strike":       actual_strike,
        "hedge_strike":       None,
        "width":              0.0,
        "entry_debit_credit": debit,
        "max_profit":         None,
        "max_loss":           max_loss,
        "target_exit_value":  target_exit,
        "stop_value":         stop_value,
        "prob_itm_proxy":     prob_itm_proxy(short_leg.get("delta", 0.5)),
        "prob_touch_proxy":   1.00,   # ATM calendar expects price to visit strike
        "contracts":          contracts,
        "confidence_score":   0,
        "notes":              notes,
        "short_dte":          short_leg["dte"],
        "long_dte":           exact_long["dte"],
        # Diagnostic fields
        "long_delta":         exact_long.get("delta"),
        "short_delta":        short_leg.get("delta"),
        "long_theta":         exact_long.get("theta"),
        "short_theta":        short_leg.get("theta"),
        "long_vega":          exact_long.get("vega"),
        "short_vega":         short_leg.get("vega"),
    }

    candidate["confidence_score"] = score_trade(candidate, market, derived)
    results.append(candidate)
    return results
