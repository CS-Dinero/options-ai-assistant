"""execution/timing_score_engine.py — Scores suitability of transition for the current session window."""
from __future__ import annotations
from typing import Any

URGENCY_MAP = {"P0":100,"P1":90,"P2":75,"P3":60,"P4":45,"P5":30,"P6":20}

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def _urgency(row): return URGENCY_MAP.get(str(row.get("bot_priority","P6")),20)

def _complexity(row):
    s=20.0
    if "FLIP" in str(row.get("transition_action","")): s+=20
    if row.get("transition_rebuild_class")=="REPLACE_LONG": s+=25
    if "SPREAD" in str(row.get("transition_action","")): s+=10
    return min(100,s)

def _window_fit(window, row):
    action=str(row.get("transition_action",""))
    urg=_urgency(row); path=_sf(row.get("transition_avg_path_score")); liq=_sf(row.get("transition_liquidity_score"))
    cx=_complexity(row); s=50.0
    if window=="OPENING_VOL":
        s+=0.20*urg+0.10*path+0.15*liq-0.20*cx
    elif window=="MORNING_TREND":
        s+=0.10*urg+0.20*path+0.15*liq
        if "DIAGONAL" in action: s+=10
    elif window=="MIDDAY":
        s+=0.05*urg+0.15*path+0.15*liq
        if "SPREAD" in action: s+=10
        if row.get("transition_rebuild_class")=="REPLACE_LONG": s-=10
    elif window=="POWER_HOUR":
        s+=0.15*urg+0.10*path+0.10*liq
        if "SPREAD" in action: s+=5
        if row.get("transition_rebuild_class")=="REPLACE_LONG": s-=5
    elif window=="LATE_CLOSE":
        s+=0.20*urg-0.20*cx
    else:
        return 0.0
    return round(max(0,min(100,s)),2)

def evaluate_timing_quality(candidate_row: dict[str,Any], session_context: dict[str,Any]) -> dict[str,Any]:
    window=session_context.get("time_window","OUTSIDE_RTH")
    ts=_window_fit(window, candidate_row)
    # Blend in surface score if available
    surf=_sf(candidate_row.get("execution_surface_score") or candidate_row.get("transition_execution_surface_score"))
    if surf>0: ts=round(0.75*ts+0.25*surf,2)
    ok=ts>=60.0
    notes=[]
    if ts>=75: notes.append("current session window is favorable for execution")
    elif ts>=60: notes.append("execution window is acceptable but not ideal")
    else: notes.append("current time window is weak for this transition")
    return {"timing_score":ts,"timing_ok":ok,"time_window":window,"notes":notes}
