"""history/trend_comparator.py — Window-vs-window and pre/post comparisons."""
from __future__ import annotations
from typing import Any

def compare_snapshot_windows(snapshots: list[dict[str,Any]], metric_key: str,
                              left_window: int=3, right_window: int=3) -> dict[str,Any]:
    ordered=sorted(snapshots, key=lambda s: s.get("timestamp_utc",""))
    if len(ordered)<left_window+right_window:
        return {"left_avg":None,"right_avg":None,"delta":None,"direction":"INSUFFICIENT_HISTORY"}
    left=ordered[-(left_window+right_window):-right_window]
    right=ordered[-right_window:]
    def _avg(group): return round(sum(float(s.get("payload",{}).get(metric_key,0)) for s in group)/len(group),4)
    la=_avg(left); ra=_avg(right); d=round(ra-la,4)
    return {"left_avg":la,"right_avg":ra,"delta":d,"direction":"UP" if d>0 else "DOWN" if d<0 else "FLAT"}
