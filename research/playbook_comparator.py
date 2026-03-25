"""research/playbook_comparator.py — Group-vs-group comparison."""
from __future__ import annotations
from typing import Any

def compare_groups(rows: list[dict[str,Any]], left_filter: dict, right_filter: dict) -> dict[str,Any]:
    def _m(r,f): return all(r.get(k)==v for k,v in f.items())
    left =[r for r in rows if _m(r,left_filter)]
    right=[r for r in rows if _m(r,right_filter)]
    def _a(g,f): vals=[float(r.get(f,0)) for r in g]; return round(sum(vals)/len(vals),3) if vals else 0.0
    def _s(g): return round(sum(1 for r in g if r.get("success"))/len(g),4) if g else 0.0
    return {"left_count":len(left),"right_count":len(right),
            "left_success_rate":_s(left),"right_success_rate":_s(right),
            "left_avg_outcome":_a(left,"outcome_score"),"right_avg_outcome":_a(right,"outcome_score"),
            "left_avg_fill":_a(left,"fill_score"),"right_avg_fill":_a(right,"fill_score"),
            "left_avg_slippage":_a(left,"slippage_dollars"),"right_avg_slippage":_a(right,"slippage_dollars")}
