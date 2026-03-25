"""surface/skew_surface_engine.py — Measures whether target short is locally rich."""
from __future__ import annotations
from typing import Any

def evaluate_skew_surface(snapshot: dict[str,Any]) -> dict[str,Any]:
    short_iv = float(snapshot.get("short_iv",0)); neighbors=[float(x) for x in snapshot.get("neighbor_ivs",[]) if float(x)>0]
    avg_n = sum(neighbors)/len(neighbors) if neighbors else 0.0
    richness = short_iv - avg_n if avg_n>0 else 0.0
    if   richness>=0.03: rs=100.0
    elif richness>=0.02: rs=85.0
    elif richness>=0.01: rs=70.0
    elif richness>=0.00: rs=55.0
    else:                rs=30.0
    ok=rs>=60.0
    notes=["target short is locally rich" if richness>0 else "target short not locally rich vs neighbors"]
    return {"surface_local_richness":round(richness,4),"surface_richness_score":round(rs,2),
            "surface_skew_ok":ok,"notes":notes}
