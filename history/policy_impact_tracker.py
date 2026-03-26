"""history/policy_impact_tracker.py — Measures operational change after a policy activation."""
from __future__ import annotations
from typing import Any

def evaluate_policy_impact(snapshots: list[dict[str,Any]], policy_version_id: str,
                            metric_key: str) -> dict[str,Any]:
    relevant=[s for s in snapshots if s.get("live_policy_version_id")]
    if not relevant: return {"policy_version_id":policy_version_id,"metric_key":metric_key,"status":"NO_HISTORY"}
    before=[s for s in relevant if s.get("live_policy_version_id")!=policy_version_id]
    after =[s for s in relevant if s.get("live_policy_version_id")==policy_version_id]
    if not before or not after:
        return {"policy_version_id":policy_version_id,"metric_key":metric_key,"status":"INSUFFICIENT_COMPARISON"}
    def _avg(group): return round(sum(float(s.get("payload",{}).get(metric_key,0)) for s in group)/len(group),4)
    ba=_avg(before); aa=_avg(after); d=round(aa-ba,4)
    return {"policy_version_id":policy_version_id,"metric_key":metric_key,
            "before_avg":ba,"after_avg":aa,"delta":d,
            "direction":"UP" if d>0 else "DOWN" if d<0 else "FLAT","status":"OK"}
