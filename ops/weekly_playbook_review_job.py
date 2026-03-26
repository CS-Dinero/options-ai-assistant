"""ops/weekly_playbook_review_job.py — Generates weekly playbook review."""
from __future__ import annotations
from reporting.weekly_playbook_review import build_weekly_playbook_review

def run_weekly_playbook_review_job(ctx: dict) -> dict:
    pv=ctx.get("live_policy_version") or {}
    return build_weekly_playbook_review(ctx["environment"],pv.get("policy_version_id"),
        ctx["playbook_stats"],ctx.get("playbook_statuses",{}),ctx.get("playbook_drag",{}))
