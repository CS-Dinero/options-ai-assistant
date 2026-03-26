"""history/snapshot_builder.py — Builds point-in-time operational snapshots."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_snapshot(snapshot_type: str, environment: str, payload: dict[str,Any],
                   live_policy_version_id: str|None=None) -> dict[str,Any]:
    return {"snapshot_id":str(uuid.uuid4()),"snapshot_type":snapshot_type,
            "environment":environment,"timestamp_utc":datetime.utcnow().isoformat(),
            "live_policy_version_id":live_policy_version_id,"payload":payload}

def build_queue_snapshot(environment: str, queue: list[dict[str,Any]],
                          live_policy_version_id: str|None=None) -> dict[str,Any]:
    ready=sum(1 for q in queue if q.get("execution_policy")=="FULL_NOW")
    stag =sum(1 for q in queue if q.get("execution_policy")=="STAGGER")
    delay=sum(1 for q in queue if q.get("execution_policy")=="DELAY")
    avg  =round(sum(float(q.get("queue_score",0)) for q in queue)/len(queue),2) if queue else 0.0
    return build_snapshot("QUEUE_SNAPSHOT",environment,live_policy_version_id=live_policy_version_id,
        payload={"queue_depth":len(queue),"avg_queue_score":avg,
                 "ready_count":ready,"stagger_count":stag,"delay_count":delay})

def build_portfolio_snapshot(environment: str, portfolio_state: dict[str,Any],
                              exposure_metrics: dict[str,Any],
                              live_policy_version_id: str|None=None) -> dict[str,Any]:
    return build_snapshot("PORTFOLIO_SNAPSHOT",environment,live_policy_version_id=live_policy_version_id,
        payload={"total_campaign_basis":portfolio_state.get("total_campaign_basis",0.0),
                 "total_unrealized_pnl":portfolio_state.get("total_unrealized_pnl",0.0),
                 "top_symbol":exposure_metrics.get("top_symbol"),
                 "top_symbol_ratio":exposure_metrics.get("top_symbol_ratio",0.0),
                 "bullish_ratio":exposure_metrics.get("bullish_ratio",0.0),
                 "bearish_ratio":exposure_metrics.get("bearish_ratio",0.0)})

def build_execution_snapshot(environment: str, metrics: dict[str,Any],
                              live_policy_version_id: str|None=None) -> dict[str,Any]:
    return build_snapshot("EXECUTION_SNAPSHOT",environment,live_policy_version_id=live_policy_version_id,
        payload={"avg_fill_score_recent":metrics.get("avg_fill_score_recent",0.0),
                 "avg_slippage_recent":metrics.get("avg_slippage_recent",0.0),
                 "delay_rate":metrics.get("delay_rate",0.0),
                 "surface_block_rate":metrics.get("surface_block_rate",0.0),
                 "timing_block_rate":metrics.get("timing_block_rate",0.0)})

def build_alert_snapshot(environment: str, alerts: list[dict[str,Any]],
                          live_policy_version_id: str|None=None) -> dict[str,Any]:
    crit=sum(1 for a in alerts if a.get("severity")=="CRITICAL")
    warn=sum(1 for a in alerts if a.get("severity")=="WARNING")
    return build_snapshot("ALERT_SNAPSHOT",environment,live_policy_version_id=live_policy_version_id,
        payload={"total_alerts":len(alerts),"critical_count":crit,"warning_count":warn})
