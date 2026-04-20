"""
position_manager/vh_triggers.py
Pure Python trigger engine for Volatility Harvest conditions.

No LLM. No side effects. Evaluates a position row + market context
and returns structured trigger dicts with flag, severity, rationale, action.

All thresholds read from config/vh_config.py for central tunability.
"""
from __future__ import annotations

from typing import Any

from config.vh_config import (
    DELTA_REDLINE, INTRINSIC_TRAP_DELTA,
    VEGA_SPIKE_MULTIPLIER, THETA_STALL_RATIO,
    GAMMA_TRAP_BUFFER, GOLD_HARVEST_MIN_CREDIT, MIN_ROLL_NET_CREDIT,
)


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "—") else d
    except (TypeError, ValueError):
        return d


def _trigger(name: str, fired: bool, severity: str, rationale: str, action: str) -> dict[str, Any]:
    return {"trigger": name, "fired": fired, "severity": severity,
            "rationale": rationale, "action": action}


# ── Individual trigger checks ─────────────────────────────────────────────────

def check_delta_redline(position: dict[str, Any]) -> dict[str, Any]:
    """Short delta approaching ITM territory — harvest or roll immediately."""
    # Support both naming conventions: short_delta (v26) and short_leg_delta (v26.1 spec)
    delta = abs(_sf(position.get("short_leg_delta") or position.get("short_delta") or position.get("delta")))
    fired = delta >= DELTA_REDLINE
    return _trigger(
        "delta_redline", fired,
        severity="HIGH" if fired else "OK",
        rationale=f"Short delta {delta:.2f} {'≥' if fired else '<'} redline {DELTA_REDLINE}",
        action="ROLL_OR_CLOSE" if fired else "HOLD",
    )


def check_vega_spike(position: dict[str, Any]) -> dict[str, Any]:
    """Current vega significantly higher than entry vega — IV expansion risk."""
    current = abs(_sf(position.get("current_vega") or position.get("vega")))
    entry   = abs(_sf(position.get("entry_vega")))
    if entry == 0:
        return _trigger("vega_spike", False, "OK", "Entry vega not recorded", "HOLD")
    ratio = current / entry
    fired = ratio >= VEGA_SPIKE_MULTIPLIER
    return _trigger(
        "vega_spike", fired,
        severity="MEDIUM" if fired else "OK",
        rationale=f"Vega ratio {ratio:.2f} {'≥' if fired else '<'} spike threshold {VEGA_SPIKE_MULTIPLIER}",
        action="EVALUATE_HARVEST" if fired else "HOLD",
    )


def check_theta_stall(position: dict[str, Any]) -> dict[str, Any]:
    """Theta decay slowing — calendar edge eroding."""
    current = abs(_sf(position.get("current_theta") or position.get("theta")))
    entry   = abs(_sf(position.get("entry_theta")))
    if entry == 0:
        return _trigger("theta_stall", False, "OK", "Entry theta not recorded", "HOLD")
    ratio = current / entry if current > 0 else 0
    fired = ratio <= (1.0 / THETA_STALL_RATIO)
    return _trigger(
        "theta_stall", fired,
        severity="LOW" if fired else "OK",
        rationale=f"Theta ratio {ratio:.2f} {'≤' if fired else '>'} stall floor {1/THETA_STALL_RATIO:.2f}",
        action="MONITOR" if fired else "HOLD",
    )


def check_gold_harvest(position: dict[str, Any], roll_credit: float) -> dict[str, Any]:
    """Roll credit meets gold-tier harvest threshold."""
    fired = roll_credit >= GOLD_HARVEST_MIN_CREDIT
    green = roll_credit >= MIN_ROLL_NET_CREDIT
    return _trigger(
        "gold_harvest", fired,
        severity="HIGH" if fired else ("MEDIUM" if green else "OK"),
        rationale=f"Proposed roll credit ${roll_credit:.2f} vs gold threshold ${GOLD_HARVEST_MIN_CREDIT:.2f}",
        action="HARVEST_GOLD" if fired else ("HARVEST_GREEN" if green else "WAIT"),
    )


def check_gamma_trap(position: dict[str, Any], trap_price: float) -> dict[str, Any]:
    """Price proximity to gamma trap wall.
    Also accepts gamma_trap_distance_pct directly if trap_price not available."""
    spot  = _sf(position.get("live_spot") or position.get("spot_price") or position.get("spot"))
    # If position already has distance_pct computed, use it directly
    if "gamma_trap_distance_pct" in position and trap_price <= 0:
        dist_pct = abs(_sf(position["gamma_trap_distance_pct"]))
        fired    = dist_pct <= GAMMA_TRAP_BUFFER
        return _trigger("gamma_trap", fired,
                        severity="HIGH" if fired else "OK",
                        rationale=f"Gamma trap distance {dist_pct:.1%} {'≤' if fired else '>'} {GAMMA_TRAP_BUFFER:.0%} buffer",
                        action="HARVEST_OR_HEDGE" if fired else "HOLD")
    if spot <= 0 or trap_price <= 0:
        return _trigger("gamma_trap", False, "OK", "Trap or spot not available", "HOLD")
    dist_pct = abs(spot - trap_price) / spot
    fired    = dist_pct <= GAMMA_TRAP_BUFFER
    return _trigger(
        "gamma_trap", fired,
        severity="HIGH" if fired else "OK",
        rationale=f"Gamma trap at ${trap_price:.2f}, spot ${spot:.2f}, distance {dist_pct:.1%} {'≤' if fired else '>'} {GAMMA_TRAP_BUFFER:.0%} buffer",
        action="HARVEST_OR_HEDGE" if fired else "HOLD",
    )


def check_assignment_risk(position: dict[str, Any]) -> dict[str, Any]:
    """Short leg deep ITM — assignment exposure."""
    delta = abs(_sf(position.get("short_delta") or position.get("delta")))
    dte   = int(_sf(position.get("short_dte") or position.get("dte"), 99))
    fired = delta >= INTRINSIC_TRAP_DELTA and dte <= 5
    return _trigger(
        "assignment_risk", fired,
        severity="CRITICAL" if fired else "OK",
        rationale=f"Short delta {delta:.2f} with {dte} DTE remaining",
        action="CLOSE_OR_ROLL_IMMEDIATELY" if fired else "HOLD",
    )


def check_skew_shift(position: dict[str, Any]) -> dict[str, Any]:
    """Put/call skew shifted since entry — may justify structure pivot."""
    entry_skew   = _sf(position.get("entry_skew"))
    current_skew = _sf(position.get("current_skew"))
    if entry_skew == 0:
        return _trigger("skew_shift", False, "OK", "Entry skew not recorded", "HOLD")
    shift = current_skew - entry_skew
    fired = abs(shift) >= 0.03   # 3 vol-point shift
    return _trigger(
        "skew_shift", fired,
        severity="MEDIUM" if fired else "OK",
        rationale=f"Skew shifted {shift:+.3f} since entry (entry={entry_skew:.3f} now={current_skew:.3f})",
        action="EVALUATE_FLIP" if fired else "HOLD",
    )


# ── Master evaluator ──────────────────────────────────────────────────────────

def evaluate_vh_triggers(
    position:   dict[str, Any],
    market_ctx: dict[str, Any],
) -> dict[str, Any]:
    """
    Run all VH trigger checks on a position.

    position    — tracked position row (from position_tracker)
    market_ctx  — derived context dict (expected_move, gamma_trap, etc.)

    Returns a dict with all trigger results plus top-line summary fields:
      any_fired, highest_severity, recommended_action, roll_credit_estimate
    """
    roll_credit  = _sf(position.get("proposed_roll_credit"))
    trap_price   = _sf(market_ctx.get("gamma_trap") or market_ctx.get("gamma_trap_strike"))

    triggers = {
        "delta_redline":   check_delta_redline(position),
        "vega_spike":      check_vega_spike(position),
        "theta_stall":     check_theta_stall(position),
        "gold_harvest":    check_gold_harvest(position, roll_credit),
        "gamma_trap":      check_gamma_trap(position, trap_price),
        "assignment_risk": check_assignment_risk(position),
        "skew_shift":      check_skew_shift(position),
    }

    sev_rank = {"OK": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    fired    = [t for t in triggers.values() if t["fired"]]
    highest  = max((sev_rank.get(t["severity"], 0) for t in fired), default=0)
    sev_map  = {v: k for k, v in sev_rank.items()}

    # Top recommended action: highest severity fired trigger wins
    top_action = "HOLD"
    if fired:
        best = max(fired, key=lambda t: sev_rank.get(t["severity"], 0))
        top_action = best["action"]

    return {
        "triggers":            triggers,
        "fired_count":         len(fired),
        "any_fired":           bool(fired),
        "highest_severity":    sev_map.get(highest, "OK"),
        "recommended_action":  top_action,
        "roll_credit_estimate": roll_credit,
    }
