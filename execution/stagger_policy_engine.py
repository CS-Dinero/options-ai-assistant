"""execution/stagger_policy_engine.py — Decides full/stagger/delay/avoid."""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"","—") else d
    except: return d

def decide_stagger_policy(candidate_row: dict[str,Any]) -> dict[str,Any]:
    ts   = _sf(candidate_row.get("transition_timing_score") or candidate_row.get("timing_score"))
    qs   = _sf(candidate_row.get("transition_queue_score"))
    ps   = _sf(candidate_row.get("transition_avg_path_score"))
    liq  = _sf(candidate_row.get("transition_liquidity_score"))
    surf = _sf(candidate_row.get("transition_execution_surface_score"))
    pri  = str(candidate_row.get("bot_priority","P6"))
    rb   = candidate_row.get("transition_rebuild_class","KEEP_LONG")

    high_urg = pri in ("P0","P1","P2")
    complex_rb = rb=="REPLACE_LONG"

    if surf < 60 and not high_urg:
        return {"execution_policy":"DELAY","size_fraction_now":0.0,"size_fraction_later":1.0,
                "notes":["surface quality weak; delay execution"]}
    if ts>=78 and liq>=70 and (high_urg or qs>=78):
        return {"execution_policy":"FULL_NOW","size_fraction_now":1.0,"size_fraction_later":0.0,
                "notes":["high-quality timing window; execute full size now"]}
    if ts>=62 and ps>=65 and liq>=60 and complex_rb:
        return {"execution_policy":"STAGGER","size_fraction_now":0.5,"size_fraction_later":0.5,
                "notes":["good structure but complex rebuild; stagger execution"]}
    if ts>=60 and qs>=70 and not high_urg:
        return {"execution_policy":"STAGGER","size_fraction_now":0.5,"size_fraction_later":0.5,
                "notes":["acceptable timing; stagger to reduce fill risk"]}
    if ts<60 and not high_urg:
        return {"execution_policy":"DELAY","size_fraction_now":0.0,"size_fraction_later":1.0,
                "notes":["timing window weak; delay execution"]}
    return {"execution_policy":"FULL_NOW","size_fraction_now":1.0,"size_fraction_later":0.0,
            "notes":["urgency overrides weaker timing"]}
