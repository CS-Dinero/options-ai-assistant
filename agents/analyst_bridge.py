"""
agents/analyst_bridge.py
Glue layer: position_tracker → harvest_engine → analyst.

build_analyst_payload() assembles the full structured context.
get_analyst_brief() returns diagnosis, harvest_move, risk_warning.
"""
from __future__ import annotations

import json
from typing import Any

from position_manager.harvest_engine import build_harvest_summary
from agents.vh_analyst_agent import analyze_position


def build_analyst_payload(
    position:        dict[str, Any],
    market_ctx:      dict[str, Any],
    harvest_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Assemble complete analyst payload.
    Computes harvest_summary if not provided.
    """
    if harvest_summary is None:
        flip_rec = position.get("flip_recommendation", "HOLD_STRUCTURE")
        harvest_summary = build_harvest_summary(position, market_ctx, flip_rec)

    return {
        "ticker":              position.get("symbol", ""),
        "tether_id":           position.get("tether_id", ""),
        "strategy":            position.get("strategy_type", ""),
        "option_side":         position.get("option_side", position.get("option_type", "")),
        "short_strike":        position.get("short_strike"),
        "long_strike":         position.get("long_strike"),
        "short_dte":           position.get("short_dte"),
        "long_dte":            position.get("long_dte"),
        "gamma_regime":        market_ctx.get("gamma_regime", ""),
        "iv_regime":           market_ctx.get("iv_regime", ""),
        "vga_environment":     market_ctx.get("vga_environment", ""),
        "net_liq":             harvest_summary.get("net_liq"),
        "proposed_roll_credit":harvest_summary.get("proposed_roll_credit"),
        "harvest_badge":       harvest_summary.get("harvest_badge"),
        "gold_harvest":        harvest_summary.get("gold_harvest"),
        "assignment_risk":     harvest_summary.get("assignment_risk"),
        "must_roll":           harvest_summary.get("must_roll"),
        "gamma_trap_distance": harvest_summary.get("gamma_trap_distance"),
        "flip_recommendation": harvest_summary.get("flip_recommendation", "HOLD_STRUCTURE"),
        "roll_action":         harvest_summary.get("roll_action"),
        "roll_notes":          harvest_summary.get("roll_notes"),
    }


def get_analyst_brief(
    position:    dict[str, Any],
    market_ctx:  dict[str, Any],
    use_llm:     bool = False,
) -> dict[str, Any]:
    """
    Build payload, run VH triggers, generate analyst brief.

    Returns:
      payload         — full structured context
      harvest_summary — harvest engine output
      brief           — {diagnosis, harvest_move, risk_warning, full_text}
    """
    from position_manager.vh_triggers import evaluate_vh_triggers
    from position_manager.harvest_engine import build_harvest_summary
    from engines.sentiment_pivot_engine import recommend_sentiment_pivot
    from engines.flip_optimizer import choose_best_flip

    # Sentiment pivot (directional gate)
    sentiment = float(position.get("sentiment_score", 0.0))
    pivot_dict = recommend_sentiment_pivot(position, market_ctx, sentiment_score=sentiment)
    flip_rec   = pivot_dict.get("pivot_recommendation", "HOLD_STRUCTURE")

    harvest_summary = build_harvest_summary(position, market_ctx, flip_rec)

    # Scored flip optimizer (v26.1)
    flip_opt = choose_best_flip(position, market_ctx)
    if flip_opt.get("flip_candidate"):
        flip_rec = flip_opt["recommendation"]

    triggers = evaluate_vh_triggers(position, market_ctx)
    position_with_triggers = {**position, "vh_triggers": triggers}

    payload = build_analyst_payload(position_with_triggers, market_ctx, harvest_summary)
    brief   = analyze_position(position_with_triggers, market_ctx, harvest_summary, use_llm=use_llm)

    return {
        "payload":         payload,
        "harvest_summary": harvest_summary,
        "triggers":        triggers,
        "flip":            flip_opt,
        "pivot":           pivot_dict,
        "brief":           brief,
    }
