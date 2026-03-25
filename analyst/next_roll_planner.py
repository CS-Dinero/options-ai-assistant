"""analyst/next_roll_planner.py — Defines the likely next management path post-execution."""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def build_next_roll_plan(row: dict[str,Any]) -> dict[str,Any]:
    action=str(row.get("transition_action","")); frs=_sf(row.get("transition_future_roll_score"))
    ps=_sf(row.get("transition_avg_path_score")); surf=_sf(row.get("transition_execution_surface_score"))
    notes=[]
    if "DIAGONAL" in action:
        notes.append("Primary plan: harvest the new short and reassess same-side roll vs basis lock after decay.")
        notes.append("Expect another roll if short remains in preferred delta zone." if frs>=70
                     else "Next roll may be selective; monitor harvestability closely.")
    elif "SPREAD" in action:
        notes.append("Primary plan: manage as defined-risk premium structure; reduce complexity if basis recovery improves.")
        notes.append("If premium compresses quickly, favor banking rather than forcing extra structure changes.")
    else:
        notes.append("Primary plan: maintain current harvest posture until a clearer structural edge appears.")
    if ps>=70 and surf>=70: notes.append("If conditions persist, follow-on premium sale should remain viable.")
    else: notes.append("Follow-on action should be more conditional due to weaker path or surface support.")
    return {"next_roll_notes":notes,"next_roll_summary":notes[0]}
