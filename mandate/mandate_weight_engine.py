"""mandate/mandate_weight_engine.py — Applies mandate weights to scoring inputs."""
from __future__ import annotations
from typing import Any
from mandate.mandate_policy import get_mandate_policy

def _sf(v, d=0.0):
    try: return float(v) if v not in (None,"") else d
    except: return d

def apply_mandate_queue_weights(row: dict[str,Any], active_mandate: str) -> dict[str,Any]:
    w = get_mandate_policy(active_mandate).get("queue_bias",{})
    out = dict(row)
    out["mandate_weighted_campaign_score"] = round(_sf(row.get("transition_campaign_improvement_score"))*_sf(w.get("campaign_improvement_score",1.0),1.0),2)
    out["mandate_weighted_recycling_score"] = round(_sf(row.get("transition_recycling_score"))*_sf(w.get("recycling_score",1.0),1.0),2)
    out["mandate_weighted_fill_score"]      = round(_sf(row.get("transition_latest_fill_score",75))*_sf(w.get("fill_score",1.0),1.0),2)
    out["mandate_weighted_allocator_score"] = round(_sf(row.get("transition_allocator_score"))*_sf(w.get("allocator_score",1.0),1.0),2)
    out["mandate_weighted_timing_score"]    = round(_sf(row.get("transition_timing_score"))*_sf(w.get("timing_score",1.0),1.0),2)
    out["mandate_weighted_surface_score"]   = round(_sf(row.get("transition_execution_surface_score"))*_sf(w.get("surface_score",1.0),1.0),2)
    out["active_mandate"] = active_mandate
    return out
