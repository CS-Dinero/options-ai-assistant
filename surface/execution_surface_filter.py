"""surface/execution_surface_filter.py — Combines skew + term structure into execution surface score."""
from __future__ import annotations
from typing import Any

def evaluate_execution_surface(skew_eval: dict[str,Any], term_eval: dict[str,Any]) -> dict[str,Any]:
    rs = float(skew_eval.get("surface_richness_score",0)); ts=float(term_eval.get("surface_term_score",0))
    hcs= float(term_eval.get("surface_harvest_curve_score",0))
    score = round(0.45*rs + 0.30*ts + 0.25*hcs, 2)
    ok    = score>=65.0
    notes=[]
    if score>=75: notes.append("surface favorable for short-leg execution now")
    elif score>=65: notes.append("surface acceptable for execution")
    else: notes.append("surface quality weak; consider waiting")
    notes.extend(skew_eval.get("notes",[])); notes.extend(term_eval.get("notes",[]))
    return {"execution_surface_score":score,"execution_surface_ok":ok,"notes":notes}
