"""history/trend_engine.py — Computes metric trends from snapshot history."""
from __future__ import annotations
from typing import Any

def _get(snapshot, key): return float(snapshot.get("payload",{}).get(key,0.0))

def compute_metric_trend(snapshots: list[dict[str,Any]], metric_key: str) -> dict[str,Any]:
    ordered=sorted(snapshots, key=lambda s: s.get("timestamp_utc",""))
    if len(ordered)<2:
        return {"latest":_get(ordered[-1],metric_key) if ordered else 0.0,
                "previous":None,"delta":None,"pct_delta":None,"direction":"INSUFFICIENT_HISTORY"}
    prev=_get(ordered[-2],metric_key); latest=_get(ordered[-1],metric_key)
    delta=round(latest-prev,4)
    pct=round((delta/prev)*100,2) if prev else None
    return {"latest":latest,"previous":prev,"delta":delta,"pct_delta":pct,
            "direction":"UP" if delta>0 else "DOWN" if delta<0 else "FLAT"}
