"""analyst/invalidation_engine.py — Defines what would weaken the selected transition."""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def build_invalidation_notes(row: dict[str,Any]) -> dict[str,Any]:
    notes=[]
    if _sf(row.get("transition_execution_surface_score"))<65:
        notes.append("Execution surface weakens; short-sale edge may no longer justify immediate execution.")
    if _sf(row.get("transition_timing_score"))<60:
        notes.append("Timing window deteriorates; transition may be better delayed or staggered.")
    if _sf(row.get("transition_worst_path_score"))<45:
        notes.append("Adverse-path robustness weak; modest unfavorable move could degrade structure quickly.")
    if _sf(row.get("transition_allocator_score"))<60:
        notes.append("Portfolio crowding worsens; allocator may no longer favor this transition.")
    if _sf(row.get("transition_campaign_improvement_score"))<60:
        notes.append("Campaign basis benefit becomes too small relative to added complexity.")
    if not notes:
        notes.append("Primary invalidation: deterioration in execution surface, timing, or campaign improvement before fill.")
    return {"invalidation_notes":notes,"invalidation_summary":notes[0]}
