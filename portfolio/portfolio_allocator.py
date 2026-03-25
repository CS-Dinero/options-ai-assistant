"""portfolio/portfolio_allocator.py — Evaluates whether a transition improves the whole book."""
from __future__ import annotations
from typing import Any

ALLOCATOR_RULES = {
    "max_bullish_ratio":        0.65,
    "max_bearish_ratio":        0.65,
    "max_symbol_concentration": 0.35,
    "max_structure_concentration": 0.50,
    "min_allocator_score":      60.0,
}

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def _infer_bias(row):
    action=str(row.get("transition_action",""))
    if "CALL" in action or "BULL" in action: return "BULLISH"
    if "PUT"  in action or "BEAR" in action: return "BEARISH"
    return str(row.get("bias","NEUTRAL")).upper()

def evaluate_portfolio_fit(
    portfolio_state:  dict[str,Any],
    exposure_metrics: dict[str,Any],
    capital_eval:     dict[str,Any],
    candidate_row:    dict[str,Any],
    rules:            dict[str,Any]|None = None,
) -> dict[str,Any]:
    R   = rules or ALLOCATOR_RULES
    sym = str(candidate_row.get("symbol",""))
    struct=str(candidate_row.get("transition_new_structure_type") or candidate_row.get("strategy_type",""))
    bias= _infer_bias(candidate_row)
    bull= _sf(exposure_metrics.get("bullish_ratio"))
    bear= _sf(exposure_metrics.get("bearish_ratio"))
    sym_c  = _sf(exposure_metrics.get("symbol_concentration",{}).get(sym,0))
    str_c  = _sf(exposure_metrics.get("structure_concentration",{}).get(struct,0))

    dir_s  = 30.0 if (bias=="BULLISH" and bull>=R["max_bullish_ratio"]) or \
                     (bias=="BEARISH" and bear>=R["max_bearish_ratio"]) else 100.0
    sym_s  = 30.0 if sym_c>=R["max_symbol_concentration"] else 100.0
    str_s  = 35.0 if str_c>=R["max_structure_concentration"] else 100.0
    cap_s  = 100.0 if capital_eval.get("capital_budget_ok",False) else 25.0
    rec_s  = _sf(capital_eval.get("recycling_score",0))

    alloc  = round(0.25*dir_s + 0.20*sym_s + 0.20*str_s + 0.20*cap_s + 0.15*rec_s, 2)
    ok     = alloc >= R["min_allocator_score"]

    notes=[]
    if dir_s<50: notes.append("directional crowding in portfolio")
    if sym_s<50: notes.append("symbol concentration too high")
    if str_s<50: notes.append("structure family concentration too high")
    if cap_s<50: notes.append("capital budget gate failed")
    if rec_s>=70: notes.append("transition recycles capital efficiently")

    return {"allocator_score":alloc, "portfolio_fit_ok":ok, "candidate_bias":bias, "notes":notes}
