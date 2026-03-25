"""research/playbook_regime_dependency_engine.py — Per-regime playbook performance."""
from __future__ import annotations
from typing import Any
from collections import defaultdict

def analyze_playbook_regime_dependency(rows: list[dict[str,Any]]) -> dict[str,Any]:
    buckets=defaultdict(list)
    for r in rows:
        c=r.get("playbook_code"); regime=r.get("vga_environment","unknown")
        if c: buckets[(c,regime)].append(float(r.get("outcome_score",0)))
    summary=defaultdict(dict)
    for (c,reg),vals in buckets.items():
        summary[c][reg]={"count":len(vals),"avg_outcome_score":round(sum(vals)/len(vals),2) if vals else 0.0}
    return {"regime_dependency":dict(summary)}
