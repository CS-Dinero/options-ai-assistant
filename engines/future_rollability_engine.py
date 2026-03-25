"""
engines/future_rollability_engine.py
Evaluates whether a proposed new structure can keep paying via future rolls.

evaluate_future_rollability(new_structure, chain_bundle, market_context)
→ dict with future_roll_score, harvestable_next_cycle, notes
"""
from __future__ import annotations

from typing import Any

from config.transition_config import ROLLABILITY_RULES


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


# ─────────────────────────────────────────────
# COMPONENT SCORERS
# ─────────────────────────────────────────────

def _score_delta_zone(delta_abs: float) -> float:
    lo = ROLLABILITY_RULES["target_short_delta_low"]
    hi = ROLLABILITY_RULES["target_short_delta_high"]
    if lo <= delta_abs <= hi:    return 100.0
    if 0.10 <= delta_abs <= 0.50: return 65.0
    if 0.05 <= delta_abs <= 0.60: return 35.0
    return 0.0


def _score_credit_ratio(next_credit: float, risk_basis: float) -> float:
    if risk_basis <= 0:
        return 0.0
    ratio  = next_credit / risk_basis
    target = ROLLABILITY_RULES["min_next_cycle_credit_ratio"]
    return max(0.0, min(100.0, (ratio / target) * 100.0)) if target > 0 else 100.0


def _score_assignment_safety(opt_type: str, strike: float, spot: float, dte: int) -> float:
    itm = 0.0
    if opt_type == "call" and spot > 0:
        itm = max(0.0, (spot - strike) / spot)
    elif opt_type == "put" and strike > 0:
        itm = max(0.0, (strike - spot) / strike)

    max_itm = ROLLABILITY_RULES["max_itm_short_pct"]
    if itm > max_itm and dte <= 7:  return 0.0
    if itm > max_itm:               return 35.0
    if dte <= 5:                    return 55.0
    return 90.0


# ─────────────────────────────────────────────
# MAIN EVALUATOR
# ─────────────────────────────────────────────

def evaluate_future_rollability(
    new_structure:  dict[str, Any],
    chain_bundle:   dict[str, list[dict]],
    market_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Evaluate whether the short leg of new_structure can keep paying next cycle.

    new_structure must have:
      short_leg   — the proposed new short option row
      current_risk_basis    — dollar risk on the structure
      expected_next_cycle_credit — estimated premium at next roll
      liquidity_score (optional)
    """
    market_context = market_context or {}
    spot       = _sf(market_context.get("spot") or market_context.get("spot_price"))
    risk_basis = _sf(new_structure.get("current_risk_basis"))
    next_credit = _sf(new_structure.get("expected_next_cycle_credit"))
    liq_score   = _sf(new_structure.get("liquidity_score"), 70.0)

    short_leg  = new_structure.get("short_leg", {})
    delta_abs  = abs(_sf(short_leg.get("delta")))
    opt_type   = str(short_leg.get("option_type", short_leg.get("option_side","call"))).lower()
    strike     = _sf(short_leg.get("strike"))
    dte        = int(_sf(short_leg.get("dte"), 7))

    delta_score      = _score_delta_zone(delta_abs)
    credit_score     = _score_credit_ratio(next_credit, risk_basis)
    assignment_score = _score_assignment_safety(opt_type, strike, spot, dte)

    future_roll_score = round(
        0.35 * credit_score +
        0.25 * delta_score +
        0.20 * assignment_score +
        0.20 * liq_score,
        2,
    )

    harvestable = (delta_score >= 65 and credit_score >= 50 and assignment_score >= 35)

    notes: list[str] = []
    notes.append(f"Short delta {delta_abs:.2f} → delta zone score {delta_score:.0f}")
    notes.append(f"Next cycle credit ${next_credit:.2f} vs risk ${risk_basis:.2f} → credit score {credit_score:.0f}")
    notes.append("Assignment risk acceptable" if assignment_score >= 35
                 else f"Assignment risk elevated (ITM short at {dte} DTE)")

    return {
        "future_roll_score":          future_roll_score,
        "expected_next_cycle_credit": round(next_credit, 4),
        "target_short_delta_zone_ok": delta_score >= 65,
        "assignment_risk_ok":         assignment_score >= 35,
        "harvestable_next_cycle":     harvestable,
        "notes":                      notes,
    }
