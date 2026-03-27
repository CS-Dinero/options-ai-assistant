"""compare/path_candidate_builder.py — Decides which paths are relevant for the current row."""
from __future__ import annotations
from typing import Any

def build_path_candidates(row: dict[str,Any]) -> list[dict[str,Any]]:
    def _sf(k,d=0.0):
        try: return float(row.get(k,d))
        except: return d
    basis=_sf("campaign_net_basis",5.0); roll=_sf("transition_future_roll_score",0.0)
    timing=_sf("transition_timing_score",70.0); surface=_sf("transition_execution_surface_score",70.0)
    recovered=_sf("campaign_recovered_pct",0.0)
    candidates=[{"path_code":"CONTINUE_HARVEST"},{"path_code":"DEFER_AND_WAIT"}]
    if roll>=55:                              candidates.append({"path_code":"ROLL_SAME_SIDE"})
    if basis<=2.0 or recovered>=60:          candidates.extend([{"path_code":"COLLAPSE_TO_SPREAD"},{"path_code":"BANK_AND_REDUCE"}])
    if timing<60 or surface<65:              candidates.append({"path_code":"DEFER_AND_WAIT"})
    seen=set(); out=[]
    for c in candidates:
        if c["path_code"] not in seen: seen.add(c["path_code"]); out.append(c)
    return out
