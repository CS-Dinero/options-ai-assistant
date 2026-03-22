"""
engines/scaling_harvest_bot.py
Priority-based action engine. Combines harvest, flip, and scale signals
into a single ranked recommendation per position.

Action priority ladder (enforced):
  EXIT_NOW   > DE_RISK     > HARVEST_NOW > FLIP_NOW
  ROLL_NOW   > SCALE_IN    > HOLD

Rules:
  - No scaling when harvest urgency is HIGH or assignment risk present
  - No scaling when position is at/above risk cap
  - Harvest beats scale
  - Exit/de-risk beats everything
  - Reinvestment capped at SCALE_MAX_CONTRACTS_PER_STEP

All thresholds read from config/vh_config.py for central tunability.
"""
from __future__ import annotations

from typing import Any

from config.vh_config import (
    GOLD_HARVEST_MIN_CREDIT, MIN_ROLL_NET_CREDIT,
    DELTA_REDLINE, INTRINSIC_TRAP_DELTA,
)

# ── Additional scaling thresholds (extend vh_config.py if needed) ─────────────
SCALE_MIN_SCORE          = 65.0   # minimum strategy score to scale
SCALE_MAX_RISK_PCT       = 0.03   # max portfolio risk pct before scaling blocked
SCALE_MAX_CONTRACTS_STEP = 2      # max contracts to add per scale event
SCALE_REINVEST_CAP_PCT   = 0.50   # max pct of harvest credit to reinvest

# Priority rank — lower number = higher priority
_PRIORITY = {
    "EXIT_NOW":    0,
    "DE_RISK":     1,
    "HARVEST_NOW": 2,
    "FLIP_NOW":    3,
    "ROLL_NOW":    4,
    "SCALE_IN":    5,
    "HOLD":        6,
}


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


def _pick(a: str, b: str) -> str:
    """Return the higher-priority action."""
    return a if _PRIORITY.get(a, 99) <= _PRIORITY.get(b, 99) else b


# ─────────────────────────────────────────────
# COMPONENT EVALUATORS
# ─────────────────────────────────────────────

def evaluate_harvest_action(
    position:   dict[str, Any],
    market_ctx: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate whether harvest/roll action is warranted."""
    roll_credit  = _sf(position.get("proposed_roll_credit"))
    must_roll    = bool(position.get("harvest_summary", {}).get("must_roll"))
    assignment   = bool(position.get("harvest_summary", {}).get("assignment_risk"))
    gold         = roll_credit >= GOLD_HARVEST_MIN_CREDIT
    green        = roll_credit >= MIN_ROLL_NET_CREDIT

    if assignment:
        return {"action": "EXIT_NOW",    "urgency": "CRITICAL",
                "rationale": f"Assignment risk — short leg ITM near expiry. Exit or roll immediately."}
    if must_roll:
        return {"action": "HARVEST_NOW", "urgency": "HIGH",
                "rationale": f"Urgent roll triggered. Proposed credit ${roll_credit:.2f}."}
    if gold:
        return {"action": "HARVEST_NOW", "urgency": "HIGH",
                "rationale": f"Gold harvest available — ${roll_credit:.2f} net credit."}
    if green:
        return {"action": "ROLL_NOW",    "urgency": "MEDIUM",
                "rationale": f"Clean roll available — ${roll_credit:.2f} net credit."}
    return {"action": "HOLD", "urgency": "LOW",
            "rationale": "No creditworthy roll available yet."}


def evaluate_flip_action(
    position:   dict[str, Any],
    market_ctx: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate whether a flip action is warranted."""
    flip_sum     = position.get("flip_summary", {})
    flip_cand    = bool(flip_sum.get("flip_candidate") or position.get("flip_candidate"))
    flip_type    = str(flip_sum.get("flip_type") or position.get("flip_recommendation","HOLD_STRUCTURE"))
    flip_credit  = _sf(flip_sum.get("flip_roll_credit") or position.get("proposed_roll_credit"))
    flip_score   = _sf(flip_sum.get("flip_quality_score") or position.get("flip_quality_score"))

    if flip_cand and flip_credit >= MIN_ROLL_NET_CREDIT and flip_score >= 20:
        return {"action": "FLIP_NOW", "urgency": "MEDIUM",
                "rationale": f"{flip_type.replace('_',' ')} — score {flip_score:.0f}, credit ${flip_credit:.2f}."}
    return {"action": "HOLD", "urgency": "LOW",
            "rationale": "No flip meets quality and credit threshold."}


def evaluate_derisk_action(
    position:   dict[str, Any],
    market_ctx: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate whether de-risk is warranted."""
    delta       = abs(_sf(position.get("short_leg_delta") or position.get("short_delta")))
    vga         = str(market_ctx.get("vga_environment","")).lower()
    gamma       = str(market_ctx.get("gamma_regime","")).lower()
    triggers    = position.get("vh_triggers", {})
    trig_list   = triggers.get("triggered", triggers.get("checks",[]))
    high_sev    = any(
        (t.get("fired") or t.get("hit")) and t.get("severity") in ("HIGH","CRITICAL")
        for t in (trig_list if isinstance(trig_list, list) else [])
    )

    bad_env = vga in ("trend_directional",) or "negative" in gamma
    redline = delta >= DELTA_REDLINE

    if redline and bad_env:
        return {"action": "DE_RISK", "urgency": "HIGH",
                "rationale": f"Delta {delta:.2f} in unfavorable environment — reduce exposure."}
    if high_sev and bad_env:
        return {"action": "DE_RISK", "urgency": "HIGH",
                "rationale": "Multiple HIGH triggers in adverse regime — de-risk."}
    return {"action": "HOLD", "urgency": "LOW", "rationale": "De-risk conditions not met."}


def evaluate_scale_action(
    position:   dict[str, Any],
    market_ctx: dict[str, Any],
    portfolio_risk_pct: float = 0.0,
) -> dict[str, Any]:
    """Evaluate whether scaling in is appropriate."""
    score       = _sf(position.get("confidence_score") or position.get("score"))
    roll_credit = _sf(position.get("proposed_roll_credit"))
    assignment  = bool(position.get("harvest_summary", {}).get("assignment_risk"))
    must_roll   = bool(position.get("harvest_summary", {}).get("must_roll"))
    contracts   = max(1, min(
        SCALE_MAX_CONTRACTS_STEP,
        int(_sf(position.get("contracts", 1)) * 0.5) or 1
    ))

    # Block scaling in these conditions
    if assignment:
        return {"action": "HOLD", "urgency": "LOW",
                "rationale": "Scale blocked — assignment risk present.", "contracts": 0}
    if must_roll:
        return {"action": "HOLD", "urgency": "LOW",
                "rationale": "Scale blocked — urgent roll pending.", "contracts": 0}
    if roll_credit >= GOLD_HARVEST_MIN_CREDIT:
        return {"action": "HOLD", "urgency": "LOW",
                "rationale": "Scale blocked — harvest first.", "contracts": 0}
    if portfolio_risk_pct >= SCALE_MAX_RISK_PCT:
        return {"action": "HOLD", "urgency": "LOW",
                "rationale": f"Scale blocked — portfolio risk at {portfolio_risk_pct:.1%}.", "contracts": 0}
    if score < SCALE_MIN_SCORE:
        return {"action": "HOLD", "urgency": "LOW",
                "rationale": f"Scale blocked — score {score:.0f} below threshold {SCALE_MIN_SCORE:.0f}.", "contracts": 0}

    return {"action": "SCALE_IN", "urgency": "LOW",
            "rationale": f"Score {score:.0f} qualifies for scale. Add {contracts} contract(s).",
            "contracts": contracts}


# ─────────────────────────────────────────────
# SCALE SIZE CALCULATOR
# ─────────────────────────────────────────────

def calculate_scale_size(
    position:    dict[str, Any],
    harvest_credit: float = 0.0,
) -> dict[str, Any]:
    """
    Calculate how many contracts to add on a scale event.

    If reinvesting harvest credit:
      - cap at SCALE_REINVEST_CAP_PCT * harvest_credit
      - never exceed SCALE_MAX_CONTRACTS_STEP
    Otherwise:
      - use half of current position size, capped
    """
    current_contracts = max(1, int(_sf(position.get("contracts", 1))))
    debit             = abs(_sf(position.get("entry_debit_credit") or position.get("avg_price"), 1.0))

    if harvest_credit > 0:
        reinvest_budget   = harvest_credit * SCALE_REINVEST_CAP_PCT * 100   # dollar budget
        affordable        = max(1, int(reinvest_budget / max(debit * 100, 1)))
        contracts_to_add  = min(affordable, SCALE_MAX_CONTRACTS_STEP)
    else:
        contracts_to_add  = min(max(1, current_contracts // 2), SCALE_MAX_CONTRACTS_STEP)

    return {
        "current_contracts":    current_contracts,
        "recommended_add":      contracts_to_add,
        "total_after_scale":    current_contracts + contracts_to_add,
        "reinvest_from_harvest": harvest_credit > 0,
    }


# ─────────────────────────────────────────────
# MASTER BOT CHOOSER
# ─────────────────────────────────────────────

def choose_bot_action(
    position:           dict[str, Any],
    market_ctx:         dict[str, Any],
    portfolio_risk_pct: float = 0.0,
) -> dict[str, Any]:
    """
    Evaluate all sub-actions and return the highest-priority one.

    Returns a complete bot summary dict with:
      bot_action             — top-level recommendation
      bot_priority           — priority rank (0=highest)
      urgency                — CRITICAL / HIGH / MEDIUM / LOW
      rationale              — plain-English reason
      recommended_contract_add — contracts to add (SCALE_IN only)
      scale_detail           — full scale size calculation
      all_actions            — all evaluated sub-actions for audit
    """
    harvest_ev = evaluate_harvest_action(position, market_ctx)
    flip_ev    = evaluate_flip_action(position, market_ctx)
    derisk_ev  = evaluate_derisk_action(position, market_ctx)
    scale_ev   = evaluate_scale_action(position, market_ctx, portfolio_risk_pct)

    # Priority ladder
    winner = "HOLD"
    for ev in [harvest_ev, flip_ev, derisk_ev, scale_ev]:
        winner = _pick(winner, ev["action"])

    # Find winning evaluator
    action_map = {
        harvest_ev["action"]: harvest_ev,
        flip_ev["action"]:    flip_ev,
        derisk_ev["action"]:  derisk_ev,
        scale_ev["action"]:   scale_ev,
    }
    winning_ev = action_map.get(winner, {"action":"HOLD","urgency":"LOW","rationale":"No action triggered."})

    # Scale size if scaling
    contracts = 0
    scale_detail = {}
    if winner == "SCALE_IN":
        sd = calculate_scale_size(position, harvest_credit=0.0)
        contracts    = sd["recommended_add"]
        scale_detail = sd

    return {
        "bot_action":              winner,
        "bot_priority":            _PRIORITY.get(winner, 6),
        "urgency":                 winning_ev.get("urgency","LOW"),
        "rationale":               winning_ev.get("rationale",""),
        "recommended_contract_add":contracts,
        "scale_detail":            scale_detail,
        "all_actions": {
            "harvest": harvest_ev,
            "flip":    flip_ev,
            "derisk":  derisk_ev,
            "scale":   scale_ev,
        },
    }


# ─────────────────────────────────────────────
# FULL BOT SUMMARY
# ─────────────────────────────────────────────

def build_bot_summary(
    position:           dict[str, Any],
    market_ctx:         dict[str, Any],
    portfolio_risk_pct: float = 0.0,
) -> dict[str, Any]:
    """Convenience wrapper — returns full bot summary dict."""
    return choose_bot_action(position, market_ctx, portfolio_risk_pct)
