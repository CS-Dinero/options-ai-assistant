"""
position_manager/harvest_engine.py
Harvest math engine — calculates net liquidation, roll credit, and harvest potential.

Hard rule: never recommend a debit roll.
If proposed roll credit < MIN_ROLL_NET_CREDIT, return action = WAIT.

All logic is pure Python. No LLM. The analyst layer (analyst_bridge.py)
uses this output to explain the move in plain English.
"""
from __future__ import annotations

from typing import Any, Optional

from config.vh_config import (
    GOLD_HARVEST_MIN_CREDIT, MIN_ROLL_NET_CREDIT,
    HARVEST_WAIT_LABEL, BADGE_GOLD, BADGE_GREEN, BADGE_RED,
    BADGE_BLUE, BADGE_WAIT, BADGE_NONE,
    GAMMA_TRAP_BUFFER, DELTA_REDLINE,
)


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


# ─────────────────────────────────────────────
# NET LIQUIDATION
# ─────────────────────────────────────────────

def get_net_liquidation(position: dict[str, Any]) -> float:
    """
    Estimate net liquidation value for a tethered position.

    Supports two naming conventions:
      v26:    current_value / mark + entry_debit_credit / avg_price
      v26.1:  long_leg_mid / short_leg_mid (tethered spread mark)

    Returns positive = gain, negative = loss.
    """
    # v26.1 spec: tethered leg midpoints
    long_mid  = _sf(position.get("long_leg_mid"))
    short_mid = _sf(position.get("short_leg_mid"))
    if long_mid or short_mid:
        qty = max(abs(int(_sf(position.get("quantity", 1)))), 1)
        return round(((long_mid - short_mid) * 100) * qty, 2)

    # v26: current_value / mark vs entry
    mark  = _sf(position.get("current_value") or position.get("mark"))
    entry = _sf(position.get("entry_debit_credit") or position.get("avg_price"))
    return round((mark - abs(entry)) * 100, 2)


# ─────────────────────────────────────────────
# ROLL CREDIT CALCULATION
# ─────────────────────────────────────────────

def calculate_harvest_credit(
    current_pos:  dict[str, Any],
    target_strike: Optional[float] = None,
    target_exp:    Optional[str]   = None,
) -> dict[str, Any]:
    """
    Estimate the net credit for rolling the current short leg to a target.

    When target_strike / target_exp are None, uses the derived roll suggestion
    embedded in the position row (from roll_manager or lifecycle adapter).

    Returns a dict with:
      gross_credit      — credit from opening new short
      buyback_cost      — cost to close existing short
      net_roll_credit   — gross_credit - buyback_cost
      creditworthy      — True if net >= MIN_ROLL_NET_CREDIT
      action            — HARVEST_GOLD / HARVEST_GREEN / WAIT
    """
    # Current short mid — support v26 (mark) and v26.1 (current_spread_cost) naming
    buyback = _sf(current_pos.get("current_spread_cost")
                  or current_pos.get("mark")
                  or current_pos.get("current_short_mid"), 0.0)

    # Proposed short premium — v26.1 uses estimated_new_credit, v26 uses roll_suggestion
    estimated_new = _sf(current_pos.get("estimated_new_credit"))
    if estimated_new > 0:
        net_credit   = round(estimated_new - buyback, 4)
        creditworthy = net_credit >= MIN_ROLL_NET_CREDIT
        action = ("HARVEST_GOLD" if net_credit >= GOLD_HARVEST_MIN_CREDIT
                  else "HARVEST_GREEN" if creditworthy else HARVEST_WAIT_LABEL)
        return {"buyback_cost": round(buyback,4), "gross_credit": round(estimated_new,4),
                "net_roll_credit": net_credit, "creditworthy": creditworthy, "action": action}

    roll_sug     = current_pos.get("roll_suggestion") or {}
    target_mid   = _sf(roll_sug.get("target_short_mid"))

    # Fall back: estimate from current mid scaled by DTE ratio
    if target_mid == 0:
        short_dte        = max(int(_sf(current_pos.get("short_dte"), 7)), 1)
        target_dte       = int(_sf(roll_sug.get("target_short_dte"), 7))
        current_short_mid = _sf(current_pos.get("mark") or current_pos.get("avg_price"))
        # Time-value scales roughly with sqrt(DTE) for ATM
        import math
        target_mid = current_short_mid * math.sqrt(target_dte / short_dte)

    net_credit   = round(target_mid - buyback, 4)
    creditworthy = net_credit >= MIN_ROLL_NET_CREDIT

    if net_credit >= GOLD_HARVEST_MIN_CREDIT:
        action = "HARVEST_GOLD"
    elif creditworthy:
        action = "HARVEST_GREEN"
    else:
        action = HARVEST_WAIT_LABEL

    return {
        "buyback_cost":     round(buyback, 4),
        "gross_credit":     round(target_mid, 4),
        "net_roll_credit":  net_credit,
        "creditworthy":     creditworthy,
        "action":           action,
    }


# ─────────────────────────────────────────────
# HARVEST POTENTIAL SUMMARY
# ─────────────────────────────────────────────

def calculate_harvest_potential(position: dict[str, Any]) -> dict[str, Any]:
    """
    Full harvest potential for a single position.

    Returns:
      net_liq               — current P/L in dollars
      harvestable_equity    — potential credit extractable via roll (net_roll_credit * 100)
      proposed_roll_credit  — per-contract roll credit
      gold_harvest          — True if meets gold threshold
      must_roll             — True if assignment/urgency demands immediate action
    """
    net_liq      = get_net_liquidation(position)
    credit_calc  = calculate_harvest_credit(position)
    roll_credit  = credit_calc["net_roll_credit"]
    harvestable  = round(roll_credit * 100, 2)   # per contract

    # Assignment / urgency from trigger state
    triggers = position.get("vh_triggers", {})
    assign   = triggers.get("assignment_risk", {}).get("fired", False)
    delta_rl = triggers.get("delta_redline",   {}).get("fired", False)
    must_roll = assign or delta_rl

    return {
        "net_liq":              net_liq,
        "harvestable_equity":   harvestable,
        "proposed_roll_credit": roll_credit,
        "gold_harvest":         roll_credit >= GOLD_HARVEST_MIN_CREDIT,
        "assignment_risk":      assign,
        "must_roll":            must_roll,
        "credit_calc":          credit_calc,
    }


# ─────────────────────────────────────────────
# CLEAN ROLL SUGGESTION
# ─────────────────────────────────────────────

def suggest_clean_roll(
    current_pos:  dict[str, Any],
    target_zone:  Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Suggest the cleanest roll available — highest net credit without going debit.

    Returns:
      target_structure    — calendar / diagonal
      target_strike       — suggested short strike for new leg
      target_expiration   — expiry label
      net_roll_credit     — estimated credit
      action              — HARVEST_GOLD / HARVEST_GREEN / WAIT
      notes
    """
    credit_info = calculate_harvest_credit(current_pos)
    roll_sug    = current_pos.get("roll_suggestion") or {}

    target_strike  = _sf(roll_sug.get("target_short_strike"))
    target_exp_str = str(roll_sug.get("target_expiration", "next expiry"))
    structure      = str(current_pos.get("strategy_type", "calendar"))

    # Diagonal if lifecycle engine recommended conversion
    lifecycle_action = str(roll_sug.get("_lifecycle_action", ""))
    if lifecycle_action == "CONVERT_TO_DIAGONAL":
        structure = "diagonal"

    return {
        "target_structure":   structure,
        "target_strike":      target_strike or None,
        "target_expiration":  target_exp_str,
        "net_roll_credit":    credit_info["net_roll_credit"],
        "action":             credit_info["action"],
        "notes": (
            "Roll is debit — do not execute." if credit_info["net_roll_credit"] < 0
            else f"Net credit ${credit_info['net_roll_credit']:.2f} per contract."
        ),
    }


# ─────────────────────────────────────────────
# ASSIGNMENT MONITOR
# ─────────────────────────────────────────────

def assignment_monitor(position: dict[str, Any]) -> dict[str, Any]:
    """
    Dedicated assignment risk assessment.

    Returns:
      at_risk       — bool
      delta         — current short delta
      dte           — days to expiry
      severity      — OK / WARNING / CRITICAL
      action
    """
    delta = abs(_sf(position.get("short_delta") or position.get("delta")))
    dte   = int(_sf(position.get("short_dte") or position.get("dte"), 99))
    side  = str(position.get("side", "short")).lower()

    if side != "short":
        return {"at_risk": False, "delta": delta, "dte": dte,
                "severity": "OK", "action": "HOLD"}

    critical = delta >= 0.75 and dte <= 3
    warning  = delta >= DELTA_REDLINE and dte <= 7

    severity = "CRITICAL" if critical else ("WARNING" if warning else "OK")
    action   = "CLOSE_IMMEDIATELY" if critical else ("ROLL_BEFORE_EXPIRY" if warning else "HOLD")

    return {"at_risk": critical or warning, "delta": round(delta, 3),
            "dte": dte, "severity": severity, "action": action}


# ─────────────────────────────────────────────
# HARVEST BADGE
# ─────────────────────────────────────────────

def compute_harvest_badge(
    position:       dict[str, Any],
    market_ctx:     dict[str, Any],
    roll_credit:    float,
    flip_rec:       str = "HOLD_STRUCTURE",
    flip_candidate: bool = False,
) -> str:
    """
    Compute the single harvest badge for display in the Positions tab.

    Priority: RED (assignment/trap) > PURPLE (flip+harvest) > GOLD > GREEN > BLUE (flip) > WAIT > —
    PURPLE = flip is recommended AND roll credit is harvestable
    """
    from config.vh_config import BADGE_PURPLE
    spot       = _sf(market_ctx.get("spot_price"))
    trap       = _sf(market_ctx.get("gamma_trap") or market_ctx.get("gamma_trap_strike"))
    assign_ctx = assignment_monitor(position)
    trap_near  = (trap > 0 and spot > 0 and abs(spot - trap) / spot <= GAMMA_TRAP_BUFFER)

    if assign_ctx["at_risk"] or trap_near:
        return BADGE_RED
    # Purple: flip candidate AND harvestable credit
    if flip_candidate and roll_credit >= MIN_ROLL_NET_CREDIT:
        return BADGE_PURPLE
    if roll_credit >= GOLD_HARVEST_MIN_CREDIT:
        return BADGE_GOLD
    if roll_credit >= MIN_ROLL_NET_CREDIT:
        return BADGE_GREEN
    if flip_rec not in ("HOLD_STRUCTURE", ""):
        return BADGE_BLUE
    if roll_credit > 0:
        return BADGE_WAIT
    return BADGE_NONE


# ─────────────────────────────────────────────
# FULL POSITION HARVEST SUMMARY
# ─────────────────────────────────────────────

def build_harvest_summary(
    position:   dict[str, Any],
    market_ctx: dict[str, Any],
    flip_rec:   str = "HOLD_STRUCTURE",
) -> dict[str, Any]:
    """
    Build the complete harvest summary dict for a single position.

    This is the primary output attached to each position row by position_tracker.
    """
    potential  = calculate_harvest_potential(position)
    roll_clean = suggest_clean_roll(position)
    assign_mon = assignment_monitor(position)

    roll_credit = potential["proposed_roll_credit"]
    spot        = _sf(market_ctx.get("spot_price"))
    trap        = _sf(market_ctx.get("gamma_trap") or market_ctx.get("gamma_trap_strike"))
    gamma_trap_dist = round(abs(spot - trap) / spot, 4) if spot > 0 and trap > 0 else None

    flip_candidate = bool(position.get("flip_candidate", False))
    badge = compute_harvest_badge(position, market_ctx, roll_credit, flip_rec, flip_candidate)

    return {
        "net_liq":              potential["net_liq"],
        "harvestable_equity":   potential["harvestable_equity"],
        "proposed_roll_credit": roll_credit,
        "gold_harvest":         potential["gold_harvest"],
        "assignment_risk":      assign_mon["at_risk"],
        "must_roll":            potential["must_roll"],
        "harvest_badge":        badge,
        "gamma_trap_distance":  gamma_trap_dist,
        "target_structure":     roll_clean["target_structure"],
        "target_strike":        roll_clean["target_strike"],
        "target_expiration":    roll_clean["target_expiration"],
        "roll_action":          roll_clean["action"],
        "roll_notes":           roll_clean["notes"],
        "assignment_detail":    assign_mon,
        "flip_recommendation":  flip_rec,
    }
