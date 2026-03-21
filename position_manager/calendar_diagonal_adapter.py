"""
position_manager/calendar_diagonal_adapter.py
Bridges calendar_diagonal_engine ↔ engine_orchestrator / dashboard.

Three functions:
  candidate_to_engine_dict(c)   — CalDiagCandidate → ranked trade card format
  decision_to_roll_dict(d)      — CalDiagDecision → roll_manager suggestion format
  run_lifecycle_monitor(positions, derived, market) → list of lifecycle signal dicts

Engine_orchestrator calls run_lifecycle_monitor() with position rows from
position_tracker.  The results surface in the Positions tab alongside credit
spread signals using the same display primitives.

Calendar candidates from strategies/calendar.py already reach the engine in the
correct ranked-trade format. This adapter handles the MANAGEMENT side only —
not entry generation.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from position_manager.calendar_diagonal_engine import (
    CalDiagConfig, OpenCalDiagPosition,
    evaluate_position, decision_to_dict,
)


# ─────────────────────────────────────────────
# 1. CANDIDATE → RANKED TRADE FORMAT
# ─────────────────────────────────────────────

def candidate_to_engine_dict(
    candidate,            # CalDiagCandidate
    *,
    symbol:   str  = "",
    vga:      str  = "",
    decision: str  = "",
) -> dict[str, Any]:
    """
    Convert a CalDiagCandidate into the ranked-trade card format expected by
    engine_orchestrator and ui_renderer.

    strategies/calendar.py already returns this format directly, so this
    function is used when you build candidates programmatically via
    build_calendar_candidate() and need to surface them in the engine output.
    """
    d = asdict(candidate)
    score = float(d.get("score", 0))

    if not decision:
        decision = "STRONG" if score >= 80 else ("TRADABLE" if score >= 65 else "SKIP")

    return {
        "strategy_type":      d["structure_type"],       # "calendar" | "diagonal"
        "direction":          f"neutral_{d['option_side']}_calendar",
        "symbol":             symbol or d["symbol"],
        "long_strike":        d["long_strike"],
        "short_strike":       d["short_strike"],
        "long_dte":           d["long_dte"],
        "short_dte":          d["short_dte"],
        "entry_debit_credit": -abs(d["entry_debit"]),   # negative = debit
        "max_loss":           d["entry_debit"] * 100,   # per-contract debit cost
        "target_exit_value":  d["target_profit_value"] * 100,
        "stop_value":         d["stop_loss_value"] * 100,
        "confidence_score":   score,
        "decision":           decision,
        "contracts":          1,
        "notes":              d["rationale"],
        "vga_environment":    vga,
        # Passthrough for position management
        "_cal_diag_candidate": d,
    }


# ─────────────────────────────────────────────
# 2. DECISION → ROLL SUGGESTION FORMAT
# ─────────────────────────────────────────────

_ACTION_TO_ROLL_ACTION = {
    "HOLD":                  "HOLD",
    "ROLL_SHORT":            "ROLL_OUT",
    "CONVERT_TO_DIAGONAL":   "CONVERT_TO_DIAGONAL",
    "ROLL_DIAGONAL_SHORT":   "ROLL_OUT",
    "EXIT_LONG_WINDOW":      "EXIT_OR_ROLL_LONG",
    "EXIT_STRUCTURE_BREAK":  "CLOSE",
    "EXIT_ENVIRONMENT":      "CLOSE",
    "NO_ACTION":             "HOLD",
    "ENTER_CALENDAR":        "HOLD",
}

_URGENCY_MAP = {
    "LOW":    "LOW",
    "MEDIUM": "MEDIUM",
    "HIGH":   "HIGH",
}


def decision_to_roll_dict(decision) -> dict[str, Any]:
    """
    Convert a CalDiagDecision into the roll_manager RollSuggestion format.

    This lets calendar/diagonal lifecycle actions surface in the same Roll
    Manager UI panel as credit spread roll suggestions.
    """
    d = asdict(decision)
    return {
        "symbol":               d["symbol"],
        "strategy":             d["structure_type"],
        "action":               _ACTION_TO_ROLL_ACTION.get(d["action"], "HOLD"),
        "urgency":              d["urgency"],
        "rationale":            d["rationale"],
        "current_spot":         d["spot"],
        "short_strike":         d["short_strike"],
        "long_strike":          d["long_strike"],
        "short_dte":            d["short_dte"],
        "long_dte":             d["long_dte"],
        "expected_move":        d["expected_move"],
        "target_short_strike":  d.get("target_short_strike"),
        "target_long_strike":   d.get("target_long_strike"),
        "target_short_dte":     d.get("target_short_dte"),
        "target_long_dte":      d.get("target_long_dte"),
        "notes":                d.get("notes", ""),
        # Keep the original lifecycle action for filtering
        "_lifecycle_action":    d["action"],
        "_option_side":         d["option_side"],
    }


# ─────────────────────────────────────────────
# 3. POSITION MONITOR LIFECYCLE RUNNER
# ─────────────────────────────────────────────

def _build_open_position(
    row:    dict[str, Any],
    spot:   float,
    vga:    str,
    gamma:  str,
    iv:     str,
    em:     float,
) -> OpenCalDiagPosition | None:
    """
    Build an OpenCalDiagPosition from a position row dict.
    Returns None if required fields are missing.
    """
    try:
        sf = lambda k, d=0.0: float(str(row.get(k, d)).replace("$","").replace(",","").strip() or d)
        si = lambda k, d=0:   int(float(row.get(k, d) or d))

        return OpenCalDiagPosition(
            symbol         = str(row.get("symbol", "")),
            structure_type = str(row.get("strategy_type", row.get("strategy", "calendar"))),
            option_side    = str(row.get("option_side", row.get("option_type", "call"))),
            long_strike    = sf("long_strike"),
            short_strike   = sf("short_strike"),
            long_dte       = si("long_dte"),
            short_dte      = si("short_dte"),
            entry_debit    = sf("entry_debit_credit") or sf("avg_price"),
            current_value  = sf("current_value") or sf("mark"),
            spot           = spot,
            expected_move  = em,
            vga_environment = vga,
            gamma_regime   = gamma,
            iv_regime      = iv,
        )
    except Exception:
        return None


def run_lifecycle_monitor(
    positions:  list[dict[str, Any]],
    *,
    derived:    dict[str, Any],
    market:     dict[str, Any],
    cfg:        CalDiagConfig | None = None,
) -> list[dict[str, Any]]:
    """
    Evaluate every open calendar/diagonal position and return a list of
    lifecycle signal dicts — one per position.

    Each dict contains:
      position_row   — the original position data
      decision       — CalDiagDecision as dict
      roll_suggestion — ready for roll_manager / roll_dashboard
      action         — top-level lifecycle action string
      urgency        — HIGH | MEDIUM | LOW
      alert_eligible — bool (True when urgency is HIGH or MEDIUM)

    Called by engine_orchestrator AFTER position_tracker.snapshot() returns
    the calendar_diagonal list.
    """
    cfg     = cfg or CalDiagConfig()
    spot    = float(market.get("spot_price", 0) or 0)
    em      = float(derived.get("expected_move", 0) or 0)
    vga     = str(derived.get("vga_environment", "mixed"))
    gamma   = str(derived.get("gamma_regime", "unknown"))
    iv      = str(derived.get("iv_regime", "unknown"))

    results: list[dict[str, Any]] = []

    for row in positions:
        strategy = str(row.get("strategy_type", row.get("strategy", ""))).lower()
        if strategy not in {"calendar", "diagonal"}:
            continue

        open_pos = _build_open_position(row, spot, vga, gamma, iv, em)
        if open_pos is None:
            continue

        decision    = evaluate_position(open_pos, cfg)
        dec_dict    = decision_to_dict(decision)
        roll_dict   = decision_to_roll_dict(decision)
        is_alert    = decision.urgency in ("HIGH", "MEDIUM")

        results.append({
            "position_row":    row,
            "decision":        dec_dict,
            "roll_suggestion": roll_dict,
            "action":          decision.action,
            "urgency":         decision.urgency,
            "alert_eligible":  is_alert,
            # Denormalized for quick dashboard display
            "symbol":          decision.symbol,
            "structure_type":  decision.structure_type,
            "option_side":     decision.option_side,
            "spot":            spot,
            "expected_move":   em,
            "long_strike":     decision.long_strike,
            "short_strike":    decision.short_strike,
            "long_dte":        decision.long_dte,
            "short_dte":       decision.short_dte,
        })

    return results
