"""prune/simplification_scoring_engine.py — Scores pruning candidates."""
from __future__ import annotations
from typing import Any

def score_pruning_candidate(candidate: dict[str,Any]) -> dict[str,Any]:
    ev=candidate.get("evidence",{}) or {}
    roi=float(ev.get("avg_roi_score",0)); friction=float(ev.get("avg_friction_score",0)); usage=int(candidate.get("usage_count",0))
    roi_press=max(0,50-roi); fric_press=min(100,friction*2)
    br=80 if usage>=20 else 60 if usage>=10 else 40 if usage>=5 else 20
    sc=max(0,100-br)
    score=round(0.35*roi_press+0.30*fric_press+0.20*sc+0.15*max(0,50-usage*3),2)
    rec="RETIRE" if score>=75 else "DEMOTE" if score>=60 else "SIMPLIFY" if score>=45 else "KEEP"
    return {**candidate,"simplify_score":score,"blast_radius":br,"safety_to_change":round(sc,2),"recommendation":rec}
