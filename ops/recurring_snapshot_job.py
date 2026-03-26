"""ops/recurring_snapshot_job.py — Queue/portfolio/execution snapshots."""
from __future__ import annotations
from history.snapshot_builder import build_queue_snapshot,build_portfolio_snapshot,build_execution_snapshot

def run_recurring_snapshot_job(ctx: dict) -> dict:
    env=ctx["environment"]; pv=ctx.get("live_policy_version") or {}; pid=pv.get("policy_version_id")
    return {"snapshots":[build_queue_snapshot(env,ctx["queue"],pid),
                          build_portfolio_snapshot(env,ctx["portfolio_state"],ctx["exposure_metrics"],pid),
                          build_execution_snapshot(env,ctx["metrics"],pid)]}
