"""ops/daily_desk_report_job.py — Generates daily desk summary."""
from __future__ import annotations
from reporting.daily_desk_summary import build_daily_desk_summary

def run_daily_desk_report_job(ctx: dict) -> dict:
    pv=ctx.get("live_policy_version") or {}
    return build_daily_desk_summary(ctx["environment"],pv.get("policy_version_id"),
        ctx.get("global_context",{}),ctx["portfolio_state"],ctx["exposure_metrics"],
        ctx["queue"],ctx["metrics"],ctx.get("alerts",[]),ctx["diagnostics"])
