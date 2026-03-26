"""ops/end_of_session_job.py — Generates operational closeout report."""
from __future__ import annotations
from reporting.report_builder import build_report_envelope

def run_end_of_session_job(ctx: dict) -> dict:
    pv=ctx.get("live_policy_version") or {}; q=ctx["queue"]; m=ctx["metrics"]; al=ctx.get("alerts",[])
    return build_report_envelope("END_OF_SESSION_REPORT",ctx["environment"],pv.get("policy_version_id"),
        "End of Session Report",
        [{"title":"Session Close","content":{"queue_depth":len(q),
          "avg_fill_score_recent":m.get("avg_fill_score_recent",0),
          "avg_slippage_recent":m.get("avg_slippage_recent",0),"alert_count":len(al)}}],
        [f"Queue at close: {len(q)}",f"Fill score: {m.get('avg_fill_score_recent',0)}",
         f"Alerts at close: {len(al)}"])
