"""research/playbook_stats_engine.py — Computes summary metrics per playbook."""
from __future__ import annotations
from typing import Any
from collections import defaultdict

def _avg(vals): return round(sum(vals)/len(vals),3) if vals else 0.0

def compute_playbook_stats(rows: list[dict[str,Any]]) -> dict[str,Any]:
    buckets=defaultdict(list)
    for r in rows: buckets[str(r.get("playbook_code","?"))].append(r)
    summary={}
    for code,items in buckets.items():
        def g(f): return [float(r.get(f,0)) for r in items]
        success_rate=round(sum(1 for r in items if r.get("success"))/len(items),4) if items else 0.0
        br=[float(r.get("campaign_basis_before",0))-float(r.get("campaign_basis_after",0)) for r in items]
        rg=[float(r.get("recovered_pct_after",0))-float(r.get("recovered_pct_before",0)) for r in items]
        summary[code]={"count":len(items),"success_rate":success_rate,
            "avg_outcome_score":_avg(g("outcome_score")),"avg_transition_credit":_avg(g("transition_credit")),
            "avg_basis_reduction":_avg(br),"avg_recovered_pct_gain":_avg(rg),
            "avg_fill_score":_avg(g("fill_score")),"avg_slippage_dollars":_avg(g("slippage_dollars")),
            "avg_path_score":_avg(g("avg_path_score")),"avg_worst_path_score":_avg(g("worst_path_score"))}
    return {"by_playbook":summary}
