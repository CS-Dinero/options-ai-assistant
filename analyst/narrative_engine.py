"""analyst/narrative_engine.py — Composes full transition narrative from sub-components."""
from __future__ import annotations
from typing import Any
from analyst.transition_explainer import explain_transition_winner
from analyst.rejection_explainer import explain_rejections
from analyst.invalidation_engine import build_invalidation_notes
from analyst.next_roll_planner import build_next_roll_plan

def build_transition_narrative(row: dict[str,Any]) -> dict[str,Any]:
    winner=explain_transition_winner(row)
    rejects=explain_rejections(row.get("transition_rejected_candidates",[]))
    invalid=build_invalidation_notes(row)
    nextroll=build_next_roll_plan(row)
    desk=(f"{winner['winner_summary']} "
          f"{rejects['rejection_summary']} "
          f"Main invalidation: {invalid['invalidation_summary']} "
          f"Next plan: {nextroll['next_roll_summary']}")
    return {**winner, **rejects, **invalid, **nextroll, "desk_note":desk}
