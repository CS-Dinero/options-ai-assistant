"""surface/vol_surface_snapshot.py — Local vol surface snapshot around candidate legs."""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def _exp(row): return str(row.get("expiry") or row.get("expiration",""))

def build_vol_surface_snapshot(chain_bundle: dict[str,list[dict]], candidate_row: dict[str,Any]) -> dict[str,Any]:
    sl  = candidate_row.get("transition_new_short_leg") or candidate_row.get("short_leg") or {}
    ll  = candidate_row.get("transition_new_long_leg")  or candidate_row.get("long_leg")  or {}
    opt = str(sl.get("option_type","call")).lower()
    short_exp = _exp(sl); short_k = _sf(sl.get("strike")); short_dte=int(_sf(sl.get("dte")))
    short_iv = _sf(sl.get("iv")); long_iv = _sf(ll.get("iv")); long_dte = int(_sf(ll.get("dte")))
    contracts = chain_bundle.get("calls",[]) if opt=="call" else chain_bundle.get("puts",[])

    # Neighbors: same exp, closest strikes
    same_exp = [c for c in contracts if _exp(c)==short_exp and _sf(c.get("iv"))>0]
    neighbors = sorted(same_exp, key=lambda c: abs(_sf(c.get("strike"))-short_k))[:3]
    neighbor_ivs = [_sf(c.get("iv")) for c in neighbors if _sf(c.get("iv"))>0]

    # Farther same strike
    farther = [c for c in contracts if abs(_sf(c.get("strike"))-short_k)<1.0 and int(_sf(c.get("dte")))>short_dte]
    farther_iv = _sf(min(farther, key=lambda c: int(_sf(c.get("dte")))-(short_dte)).get("iv")) if farther else 0.0

    return {"option_type":opt,"short_iv":short_iv,"long_iv":long_iv,
            "short_dte":short_dte,"long_dte":long_dte,"short_strike":short_k,
            "neighbor_ivs":neighbor_ivs,"farther_same_strike_iv":farther_iv}
