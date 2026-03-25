"""portfolio/portfolio_state.py — Normalized snapshot of the whole book."""
from __future__ import annotations
from typing import Any
from collections import defaultdict

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def build_portfolio_state(rows: list[dict[str,Any]]) -> dict[str,Any]:
    sym_counts=defaultdict(int); struct_counts=defaultdict(int)
    sym_basis=defaultdict(float); sym_unreal=defaultdict(float)
    total_basis=0.0; total_unreal=0.0; total_short_prem=0.0
    bull=0; bear=0; neutral=0

    for r in rows:
        sym=str(r.get("symbol","UNKNOWN")); struct=str(r.get("strategy_type") or r.get("structure_type","UNKNOWN"))
        basis=_sf(r.get("campaign_net_basis") or r.get("net_liq"))
        unreal=_sf(r.get("unrealized_pnl") or r.get("net_liq"))
        sl=r.get("short_leg") or {}; sm=_sf(sl.get("mid")); qty=max(1,int(_sf(r.get("contracts",1))))
        sym_counts[sym]+=1; struct_counts[struct]+=1
        sym_basis[sym]+=basis; sym_unreal[sym]+=unreal
        total_basis+=basis; total_unreal+=unreal; total_short_prem+=sm*qty
        bias=str(r.get("bias","")).lower()
        ta=str(r.get("transition_action") or r.get("direction","")).lower()
        if "bull" in bias or "call_diag" in ta or "bull_put" in ta: bull+=1
        elif "bear" in bias or "put_diag" in ta or "bear_call" in ta: bear+=1
        else: neutral+=1

    return {
        "position_count":           len(rows),
        "symbol_counts":            dict(sym_counts),
        "structure_counts":         dict(struct_counts),
        "symbol_basis":             {k:round(v,2) for k,v in sym_basis.items()},
        "symbol_unrealized":        {k:round(v,2) for k,v in sym_unreal.items()},
        "total_campaign_basis":     round(total_basis,2),
        "total_unrealized_pnl":     round(total_unreal,2),
        "total_short_premium_outstanding": round(total_short_prem,2),
        "bullish_count":  bull,
        "bearish_count":  bear,
        "neutral_count":  neutral,
    }
