"""analyst/desk_summary_engine.py — One-liner summaries for cockpit display."""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def build_queue_one_liner(row: dict[str,Any]) -> str:
    sym=row.get("symbol","?"); action=row.get("transition_action","?").replace("_"," ").title()
    credit=_sf(row.get("transition_net_credit")); pol=row.get("transition_execution_policy","?")
    ba=_sf(row.get("transition_campaign_net_basis_after"))
    return f"{sym} {action} | ${credit:.2f} | {pol} | basis→${ba:.2f}"

def build_blocked_one_liner(row: dict[str,Any]) -> str:
    sym=row.get("symbol","?"); reasons=[]
    if row.get("transition_execution_surface_ok") is False: reasons.append("surface")
    if row.get("transition_timing_ok") is False: reasons.append("timing")
    if row.get("transition_portfolio_fit_ok") is False: reasons.append("portfolio")
    return f"{sym} blocked by {', '.join(reasons) if reasons else 'unspecified'}"

def build_campaign_one_liner(row: dict[str,Any]) -> str:
    sym=row.get("symbol","?"); rec=_sf(row.get("campaign_recovered_pct"))
    basis=_sf(row.get("campaign_net_basis")); cycles=int(_sf(row.get("campaign_harvest_cycles")))
    return f"{sym} recovered {rec:.1f}% | basis ${basis:.2f} | {cycles} harvest cycles"
