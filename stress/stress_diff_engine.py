"""stress/stress_diff_engine.py — Baseline vs stressed behavioral comparison."""
from __future__ import annotations
from typing import Any

def build_stress_diff(baseline_metrics: dict[str,Any], stressed_metrics: dict[str,Any],
                       baseline_queue: list[dict[str,Any]], stressed_queue: list[dict[str,Any]],
                       baseline_alerts: list[dict[str,Any]], stressed_alerts: list[dict[str,Any]],
                       baseline_refinements: list[dict[str,Any]]|None=None,
                       stressed_refinements: list[dict[str,Any]]|None=None) -> dict[str,Any]:
    def _m(m,k): return float(m.get(k,0.0))
    return {
        "queue_depth_delta":        len(stressed_queue)-len(baseline_queue),
        "blocked_rate_delta":       round(_m(stressed_metrics,"blocked_candidate_rate")-_m(baseline_metrics,"blocked_candidate_rate"),4),
        "fill_score_delta":         round(_m(stressed_metrics,"avg_fill_score_recent")-_m(baseline_metrics,"avg_fill_score_recent"),2),
        "top_symbol_concentration_delta": round(_m(stressed_metrics,"top_symbol_concentration")-_m(baseline_metrics,"top_symbol_concentration"),4),
        "alert_count_delta":        len(stressed_alerts)-len(baseline_alerts),
        "refinement_count_delta":   len(stressed_refinements or [])-len(baseline_refinements or []),
    }
