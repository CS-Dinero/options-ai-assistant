"""ops/policy_followup_job.py — Generates policy impact memo after activation."""
from __future__ import annotations
from reporting.policy_impact_memo import build_policy_impact_memo

def run_policy_followup_job(ctx: dict) -> dict:
    pv=ctx.get("live_policy_version") or {}
    return build_policy_impact_memo(ctx["environment"],pv.get("policy_version_id","?"),
        ctx.get("policy_impact_rows",[]))
