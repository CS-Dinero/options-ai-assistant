"""analyst/transition_explainer.py — Explains why the selected transition won."""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def explain_transition_winner(row: dict[str,Any]) -> dict[str,Any]:
    action=str(row.get("transition_action","UNKNOWN")); credit=_sf(row.get("transition_net_credit"))
    camp=_sf(row.get("transition_campaign_improvement_score")); path=_sf(row.get("transition_avg_path_score"))
    alloc=_sf(row.get("transition_allocator_score")); ts=_sf(row.get("transition_timing_score"))
    surf=_sf(row.get("transition_execution_surface_score")); rb=row.get("transition_rebuild_class","KEEP_LONG")
    reasons=[]
    if credit>0: reasons.append(f"Pays net credit now (${credit:.2f}/share)")
    if camp>=70: reasons.append("Meaningfully improves campaign basis recovery")
    if path>=70: reasons.append("Remains robust across tested forward paths")
    if alloc>=70: reasons.append("Fits portfolio posture without crowding")
    if ts>=70:   reasons.append("Timing window favorable for execution")
    if surf>=70: reasons.append("Short-leg surface is rich enough to sell now")
    if rb=="REPLACE_LONG": reasons.append("Replacing long materially improved structure quality")
    else: reasons.append("Keeping long preserved simplicity and reduced churn")
    summary=f"{action.replace('_',' ')}: selected because it pays now, preserves future harvestability, and ranks best on campaign + path + execution quality."
    return {"winner_reasons":reasons,"winner_summary":summary}
