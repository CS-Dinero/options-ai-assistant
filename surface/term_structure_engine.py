"""surface/term_structure_engine.py — Checks front/back month vol relationship."""
from __future__ import annotations
from typing import Any

def evaluate_term_structure(snapshot: dict[str,Any]) -> dict[str,Any]:
    short_iv=float(snapshot.get("short_iv",0)); farther_iv=float(snapshot.get("farther_same_strike_iv",0))
    long_iv=float(snapshot.get("long_iv",0))
    fb_edge = short_iv-farther_iv if farther_iv>0 else 0.0
    ls_edge = short_iv-long_iv    if long_iv>0    else 0.0
    if   fb_edge>=0.02: ts=90.0
    elif fb_edge>=0.01: ts=75.0
    elif fb_edge>=0.00: ts=60.0
    else:               ts=35.0
    hcs = 80.0 if ls_edge>=0 else 60.0 if ls_edge>=-0.01 else 35.0
    ok  = ts>=60.0
    notes=[]
    notes.append("front month rich vs farther expiry" if fb_edge>0 else "front month not rich vs farther expiry")
    notes.append("short IV favorable vs long leg" if ls_edge>0 else "long leg absorbing vol premium")
    return {"surface_front_back_edge":round(fb_edge,4),"surface_long_short_edge":round(ls_edge,4),
            "surface_term_score":round(ts,2),"surface_harvest_curve_score":round(hcs,2),
            "surface_term_ok":ok,"notes":notes}
