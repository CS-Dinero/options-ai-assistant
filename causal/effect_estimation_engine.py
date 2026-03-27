"""causal/effect_estimation_engine.py — Difference-in-differences style effect estimation."""
from __future__ import annotations
from typing import Any

def _avg(rows, key):
    return sum(float(r.get(key,0)) for r in rows)/len(rows) if rows else 0.0

def estimate_effect(treated_before: list[dict[str,Any]], treated_after: list[dict[str,Any]],
                    comp_before: list[dict[str,Any]], comp_after: list[dict[str,Any]],
                    metric_key: str) -> dict[str,Any]:
    tb=_avg(treated_before,metric_key); ta=_avg(treated_after,metric_key)
    cb=_avg(comp_before,metric_key);   ca=_avg(comp_after,metric_key)
    td=ta-tb; cd=ca-cb; eff=td-cd
    return {"metric_key":metric_key,"treated_before":round(tb,4),"treated_after":round(ta,4),
            "comparison_before":round(cb,4),"comparison_after":round(ca,4),
            "treated_delta":round(td,4),"comparison_delta":round(cd,4),"estimated_effect":round(eff,4)}
