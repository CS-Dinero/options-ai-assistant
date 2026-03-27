"""prune/merge_detection_engine.py — Finds overlapping components that could be merged."""
from __future__ import annotations
from typing import Any

def detect_merge_candidates(component_stats: dict[str,Any]) -> list[dict[str,Any]]:
    items=list(component_stats.items()); candidates=[]
    for i in range(len(items)):
        a_id,a=items[i]
        for j in range(i+1,len(items)):
            b_id,b=items[j]
            roi_gap=abs(float(a.get("avg_roi_score",0))-float(b.get("avg_roi_score",0)))
            fric_gap=abs(float(a.get("avg_friction_score",0))-float(b.get("avg_friction_score",0)))
            if roi_gap<=5.0 and fric_gap<=5.0:
                candidates.append({"left_component_id":a_id,"right_component_id":b_id,
                                    "reason":"highly similar ROI and friction profile",
                                    "merge_score":round(100-roi_gap*5-fric_gap*5,2)})
    candidates.sort(key=lambda x: x["merge_score"],reverse=True)
    return candidates
