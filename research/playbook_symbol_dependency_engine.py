"""research/playbook_symbol_dependency_engine.py — Per-symbol playbook performance."""
from __future__ import annotations
from typing import Any
from collections import defaultdict

def analyze_playbook_symbol_dependency(rows: list[dict[str,Any]]) -> dict[str,Any]:
    buckets=defaultdict(list)
    for r in rows:
        c=r.get("playbook_code"); sym=r.get("symbol")
        if c and sym: buckets[(c,sym)].append(float(r.get("outcome_score",0)))
    summary=defaultdict(dict)
    for (c,sym),vals in buckets.items():
        summary[c][sym]={"count":len(vals),"avg_outcome_score":round(sum(vals)/len(vals),2) if vals else 0.0}
    return {"symbol_dependency":dict(summary)}
