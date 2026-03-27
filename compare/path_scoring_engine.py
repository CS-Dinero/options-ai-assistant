"""compare/path_scoring_engine.py — Scores each path across multiple dimensions."""
from __future__ import annotations
from typing import Any

def _sf(row,k,d=0.0):
    try: return float(row.get(k,d))
    except: return d

def score_path(path_code: str, row: dict[str,Any], active_mandate: str) -> dict[str,Any]:
    basis=_sf(row,"campaign_net_basis",5.0); recovered=_sf(row,"campaign_recovered_pct",0.0)
    roll=_sf(row,"transition_future_roll_score",0.0); timing=_sf(row,"transition_timing_score",70.0)
    surface=_sf(row,"transition_execution_surface_score",70.0); fill=_sf(row,"transition_latest_fill_score",75.0)
    br=ec=ce=si=rp=50.0
    if path_code=="CONTINUE_HARVEST":
        br=min(100,55+roll*0.4); ec=(timing+surface+fill)/3; ce=55; si=45; rp=55
    elif path_code=="ROLL_SAME_SIDE":
        br=min(100,60+roll*0.45); ec=(timing+surface+fill)/3; ce=60; si=50; rp=50
    elif path_code=="COLLAPSE_TO_SPREAD":
        br=min(100,45+recovered*0.4); ec=min(100,55+fill*0.25); ce=75; si=80; rp=35
    elif path_code=="BANK_AND_REDUCE":
        br=min(100,40+recovered*0.35); ec=70; ce=90; si=90; rp=25
    elif path_code=="DEFER_AND_WAIT":
        br=35; ec=min(100,65+max(0,70-min(timing,surface))*0.1); ce=65; si=85; rp=45
    mf=60.0
    if active_mandate=="BASIS_RECOVERY"              and path_code in ("CONTINUE_HARVEST","ROLL_SAME_SIDE"): mf=85
    elif active_mandate=="CAPITAL_PRESERVATION"      and path_code in ("BANK_AND_REDUCE","COLLAPSE_TO_SPREAD"): mf=85
    elif active_mandate=="EXECUTION_QUALITY"         and path_code in ("DEFER_AND_WAIT","BANK_AND_REDUCE"): mf=80
    elif active_mandate=="QUEUE_HEALTH"              and path_code in ("CONTINUE_HARVEST","DEFER_AND_WAIT"): mf=75
    total=round(0.25*br+0.20*ec+0.20*ce+0.15*si+0.10*(100-rp)+0.10*mf,2)
    return {"path_code":path_code,"basis_recovery_score":round(br,2),"execution_quality_score":round(ec,2),
            "capital_efficiency_score":round(ce,2),"simplicity_score":round(si,2),
            "review_pressure_score":round(rp,2),"mandate_fit_score":round(mf,2),"path_total_score":total}
