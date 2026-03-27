"""causal/before_after_engine.py — Measures pre/post shifts for the treated group."""
from __future__ import annotations
from typing import Any

def _avg(rows, key):
    return round(sum(float(r.get(key,0)) for r in rows)/len(rows),4) if rows else 0.0

TRACKED_METRICS = ["outcome_score","fill_score","slippage_dollars","friction_score","roi_score"]

def build_before_after_summary(before_rows: list[dict[str,Any]], after_rows: list[dict[str,Any]]) -> dict[str,Any]:
    return {k:{"before_avg":_avg(before_rows,k),"after_avg":_avg(after_rows,k),
               "delta":round(_avg(after_rows,k)-_avg(before_rows,k),4)} for k in TRACKED_METRICS}
