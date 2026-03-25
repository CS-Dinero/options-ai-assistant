"""
engines/path_expectancy_scorer.py
Scores a transition candidate across all forward path scenarios.
Uses heuristic mechanics — not a full pricing model.
"""
from __future__ import annotations
from typing import Any
from position_manager.campaign_memory import compute_campaign_net_basis

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def _safe_mid(c):
    m=_sf(c.get("mid")); return m if m>0 else round((_sf(c.get("bid"))+_sf(c.get("ask")))/2,4)

def _short_decay_score(sl, scenario):
    da=abs(_sf(sl.get("delta"))); gamma=scenario["gamma_regime"]; mp=abs(_sf(scenario["spot_move_pct"]))
    s=50.0
    if 0.18<=da<=0.35: s+=25
    elif 0.10<=da<=0.42: s+=15
    if gamma=="positive": s+=15
    elif gamma=="negative": s-=10
    if mp>=0.03: s-=10
    return round(max(0,min(100,s)),2)

def _assign_risk(sl, scen_spot):
    opt=str(sl.get("option_type","")).lower(); k=_sf(sl.get("strike")); dte=int(_sf(sl.get("dte")))
    itm=max(0.0,(scen_spot-k)/scen_spot) if opt=="call" and scen_spot>0 else max(0.0,(k-scen_spot)/k) if opt=="put" and k>0 else 0.0
    r=20.0
    if itm>0.01: r+=20
    if itm>0.03: r+=25
    if dte<=7: r+=15
    if dte<=3: r+=15
    return round(max(0,min(100,r)),2)

def _rollability(sl, scenario):
    da=abs(_sf(sl.get("delta"))); gamma=scenario["gamma_regime"]
    s=50.0
    if 0.18<=da<=0.42: s+=25
    elif 0.10<=da<=0.50: s+=10
    if gamma=="positive": s+=10
    elif gamma=="negative": s-=5
    return round(max(0,min(100,s)),2)

def _resilience(ll, sl, scenario):
    if not ll: return 60.0
    ld=abs(_sf(ll.get("delta"))); sd=abs(_sf(sl.get("delta"))); mp=abs(_sf(scenario["spot_move_pct"]))
    s=50.0
    if ld>=0.65: s+=20
    if sd<=0.35: s+=10
    if mp<=0.015: s+=10
    if mp>=0.03: s-=10
    return round(max(0,min(100,s)),2)

def score_candidate_across_paths(
    current_position:    dict[str, Any],
    candidate_structure: dict[str, Any],
    campaign_memory:     dict[str, Any],
    scenarios:           list[dict[str, Any]],
) -> dict[str, Any]:
    sl      = candidate_structure.get("short_leg",{}) or {}
    ll      = candidate_structure.get("long_leg")
    credit  = _sf(candidate_structure.get("transition_net_credit"))
    basis_b = compute_campaign_net_basis(campaign_memory)
    results = []
    for sc in scenarios:
        ss=_sf(sc["spot_scenario"])
        decay=_short_decay_score(sl,sc); assing=_assign_risk(sl,ss)
        roll=_rollability(sl,sc); res=_resilience(ll,sl,sc)
        path_s=round(0.30*decay+0.25*roll+0.20*res+0.15*max(0,100-assing)+0.10*max(0,min(100,credit*50)),2)
        results.append({
            "scenario_name":sc["scenario_name"],"label":sc["label"],
            "spot_scenario":ss,"short_decay_score":decay,
            "rollability_score":roll,"assignment_risk_score":assing,
            "resilience_score":res,"basis_after":round(basis_b-credit,4),"path_score":path_s,
        })
    avg  = round(sum(r["path_score"] for r in results)/len(results),2) if results else 0.0
    worst= round(min(r["path_score"] for r in results),2) if results else 0.0
    best = round(max(r["path_score"] for r in results),2) if results else 0.0
    robust = avg>=65.0 and worst>=45.0
    notes=[]
    if robust: notes.append("candidate remains acceptable across tested paths")
    if worst<40: notes.append("fragile under adverse scenario path")
    if best-worst>30: notes.append("highly path-sensitive transition")
    return {"scenario_results":results,"avg_path_score":avg,"worst_path_score":worst,
            "best_path_score":best,"path_robust":robust,"notes":notes}
