"""attribution/interaction_attribution_engine.py — Measures layer combinations."""
from __future__ import annotations
from typing import Any
from collections import defaultdict
from attribution.value_signal_engine import compute_value_signals
from attribution.friction_signal_engine import compute_friction_signals
from attribution.roi_scoring_engine import compute_component_roi

def attribute_interactions(rows: list[dict[str,Any]], left_field: str, right_field: str) -> dict[str,Any]:
    buckets=defaultdict(list)
    for r in rows: buckets[(r.get(left_field,"?"),r.get(right_field,"?"))].append(r)
    out={}
    for key,items in buckets.items():
        rois=[compute_component_roi(compute_value_signals(r),compute_friction_signals(r))["roi_score"] for r in items]
        out[str(key)]={"count":len(items),"avg_roi_score":round(sum(rois)/len(rois),2) if rois else 0.0}
    return out
