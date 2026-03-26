"""monitoring/rollback_watch_engine.py — Flags live policy degradation conditions."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def evaluate_rollback_watch(metrics: dict[str,Any], live_policy_version: dict[str,Any]|None) -> list[dict[str,Any]]:
    if not live_policy_version: return []
    alerts=[]; vid=live_policy_version.get("policy_version_id")
    def _evt(metric,severity,summary):
        return {"alert_id":str(uuid.uuid4()),"timestamp_utc":datetime.utcnow().isoformat(),
                "severity":severity,"metric_name":metric,"summary":summary,"live_policy_version_id":vid}
    if metrics.get("avg_fill_score_recent",100)<=55.0:
        alerts.append(_evt("avg_fill_score_recent","CRITICAL",
            "Rollback watch: fill quality deteriorated materially under live policy."))
    if metrics.get("queue_depth",99)<=1:
        alerts.append(_evt("queue_depth","WARNING",
            "Rollback watch: queue depth unusually low under live policy."))
    if metrics.get("blocked_candidate_rate",0.0)>=0.60:
        alerts.append(_evt("blocked_candidate_rate","WARNING",
            "Rollback watch: candidate block rate abnormally high under live policy."))
    return alerts
