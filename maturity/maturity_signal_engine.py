"""maturity/maturity_signal_engine.py — Extracts maturity signals from operational rows."""
from __future__ import annotations
from typing import Any

def _sf(v,d=0.0):
    try: return float(v) if v not in(None,"") else d
    except: return d

def compute_maturity_signals(capability_id: str, rows: list[dict[str,Any]]) -> dict[str,Any]:
    n=max(1,len(rows))
    avg_roi=sum(_sf(r.get("roi_score")) for r in rows)/n
    avg_friction=sum(_sf(r.get("friction_score")) for r in rows)/n
    overrides=sum(int(r.get("decision_override_count",0)) for r in rows)
    failures=sum(1 for r in rows if r.get("blocked_flag")==1)
    stability=max(0.0,100.0-avg_friction)
    return {"capability_id":capability_id,"usage":len(rows),"avg_roi":round(avg_roi,2),
            "avg_friction":round(avg_friction,2),"override_rate":round(overrides/n,4),
            "failure_rate":round(failures/n,4),"stability_score":round(stability,2)}
