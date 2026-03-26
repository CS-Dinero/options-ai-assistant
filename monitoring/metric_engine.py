"""monitoring/metric_engine.py — Computes current operational metrics."""
from __future__ import annotations
from typing import Any

def _ratio(num,den):
    return round(num/den,4) if den else 0.0

def compute_operational_metrics(
    rows: list[dict[str,Any]], queue: list[dict[str,Any]],
    slippage_model: dict[str,Any], playbook_stats: dict[str,Any],
    exposure_metrics: dict[str,Any],
) -> dict[str,Any]:
    n = max(1,len(rows))
    blocked   = sum(1 for r in rows if (r.get("transition_execution_surface_ok") is False or
                                         r.get("transition_timing_ok") is False or
                                         r.get("transition_portfolio_fit_ok") is False or
                                         r.get("capital_commitment_ok") is False))
    surf_blk  = sum(1 for r in rows if r.get("transition_execution_surface_ok") is False)
    time_blk  = sum(1 for r in rows if r.get("transition_timing_ok") is False)
    cap_blk   = sum(1 for r in rows if r.get("capital_commitment_ok") is False)
    delayed   = sum(1 for r in rows if r.get("transition_execution_policy")=="DELAY")

    by_policy = slippage_model.get("by_policy",{})
    avg_fill=0.0; avg_slip=0.0
    if by_policy:
        vals=list(by_policy.values())
        avg_fill=round(sum(v.get("avg_fill_score",0) for v in vals)/len(vals),2)
        avg_slip=round(sum(v.get("avg_slippage_dollars",0) for v in vals)/len(vals),3)

    return {
        "avg_fill_score_recent":         avg_fill,
        "avg_slippage_recent":           avg_slip,
        "blocked_candidate_rate":        _ratio(blocked,n),
        "surface_block_rate":            _ratio(surf_blk,n),
        "timing_block_rate":             _ratio(time_blk,n),
        "queue_depth":                   len(queue),
        "queue_compression_rate":        _ratio(max(0,n-5),n),
        "top_symbol_concentration":      float(exposure_metrics.get("top_symbol_ratio",0)),
        "capital_block_rate":            _ratio(cap_blk,n),
        "delay_rate":                    _ratio(delayed,n),
        "promoted_playbook_outcome_drift":0.0,
    }
