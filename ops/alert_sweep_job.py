"""ops/alert_sweep_job.py — Recomputes metrics and refreshes alert state."""
from __future__ import annotations
from monitoring.threshold_registry import get_thresholds
from monitoring.alert_rule_engine import build_alerts
from monitoring.rollback_watch_engine import evaluate_rollback_watch

def run_alert_sweep_job(ctx: dict) -> dict:
    env=ctx.get("environment","DEV"); metrics=ctx["metrics"]
    pv=ctx.get("live_policy_version")
    alerts=build_alerts(metrics,get_thresholds(env),env)
    rw=evaluate_rollback_watch(metrics,pv)
    return {"alerts":alerts+rw}
