"""execution/fill_quality_engine.py — Scores expected vs actual execution credit."""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def _fill_score(expected, actual):
    if expected<=0: return 0.0
    r=actual/expected
    if r>=1.00: return 100.0
    if r>=0.95: return 85.0
    if r>=0.90: return 70.0
    if r>=0.80: return 50.0
    return 20.0

def evaluate_fill_quality(ticket: dict[str,Any], execution_result: dict[str,Any]) -> dict[str,Any]:
    exp  = _sf(ticket.get("estimated_net_credit"))
    act  = _sf(execution_result.get("actual_net_credit", exp))
    mid  = _sf(ticket.get("estimated_mid_credit", exp))
    slip = round(act-exp,4); slip_mid=round(act-mid,4)
    slip_pct=round((slip/exp)*100,2) if exp>0 else 0.0
    fs   = _fill_score(exp,act)
    notes=[]
    notes.append("fill met conservative estimate" if slip>=0 else "fill below conservative estimate")
    if slip_mid<0: notes.append("fill below mid, as expected in live conditions")
    return {"expected_credit":exp,"expected_mid_credit":mid,"actual_credit":act,
            "slippage_dollars":slip,"slippage_vs_mid":slip_mid,"slippage_pct":slip_pct,
            "fill_score":fs,"notes":notes}
