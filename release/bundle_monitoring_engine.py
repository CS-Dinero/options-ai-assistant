"""release/bundle_monitoring_engine.py — Defines what to watch after rollout."""
from __future__ import annotations
from typing import Any

def build_bundle_monitoring_plan(bundle_type: str) -> dict[str,Any]:
    metrics=["avg_fill_score_recent","blocked_candidate_rate","queue_depth",
             "top_symbol_concentration","capital_block_rate"]
    if bundle_type=="EXECUTION_HARDENING_BUNDLE": metrics.extend(["avg_slippage_recent","delay_rate"])
    if bundle_type=="QUEUE_HEALTH_BUNDLE":        metrics.extend(["surface_block_rate","timing_block_rate","queue_compression_rate"])
    if bundle_type=="PLAYBOOK_STATUS_BUNDLE":      metrics.extend(["promoted_playbook_outcome_drift"])
    return {"watch_metrics":metrics,"watch_alerts":["rollback_watch","critical_execution","queue_starvation"]}
