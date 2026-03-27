"""stress/stress_scoring_engine.py — Resilience score for a stress scenario."""
from __future__ import annotations
from typing import Any

def score_stress_resilience(diff: dict[str,Any]) -> dict[str,Any]:
    def _sf(k): return float(diff.get(k,0.0))
    qs=max(0.0,100.0-max(0,-int(_sf("queue_depth_delta")))*20.0)
    bs=max(0.0,100.0-max(0.0,_sf("blocked_rate_delta"))*150.0)
    fs=max(0.0,100.0+_sf("fill_score_delta")*3.0)
    als=max(0.0,100.0-max(0,_sf("alert_count_delta"))*10.0)
    cs=max(0.0,100.0-max(0.0,_sf("top_symbol_concentration_delta"))*200.0)
    score=round(0.20*qs+0.25*bs+0.20*fs+0.15*als+0.20*cs,2)
    status="ROBUST" if score>=75 else "STABLE" if score>=60 else "FRAGILE"
    return {"resilience_score":score,"status":status,
            "component_scores":{"queue_score":round(qs,2),"block_score":round(bs,2),
                                  "fill_score":round(fs,2),"alert_score":round(als,2),
                                  "concentration_score":round(cs,2)}}
