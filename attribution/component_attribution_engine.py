"""attribution/component_attribution_engine.py — Aggregates ROI by component."""
from __future__ import annotations
from typing import Any
from collections import defaultdict
from attribution.value_signal_engine import compute_value_signals
from attribution.friction_signal_engine import compute_friction_signals
from attribution.roi_scoring_engine import compute_component_roi

def _avg(vals): return round(sum(vals)/len(vals),2) if vals else 0.0

def attribute_by_component(rows: list[dict[str,Any]], component_field: str) -> dict[str,Any]:
    buckets=defaultdict(list)
    for r in rows: buckets[r.get(component_field,"UNKNOWN")].append(r)
    out={}
    for key,items in buckets.items():
        rois=[]; vals=[]; frics=[]
        for r in items:
            v=compute_value_signals(r); f=compute_friction_signals(r); roi=compute_component_roi(v,f)
            rois.append(roi["roi_score"]); vals.append(roi["value_score"]); frics.append(roi["friction_score"])
        out[key]={"count":len(items),"avg_roi_score":_avg(rois),"avg_value_score":_avg(vals),"avg_friction_score":_avg(frics)}
    return out
