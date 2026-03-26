"""reporting/rollback_recommendation_report.py — Structured rollback review justification."""
from __future__ import annotations
from typing import Any
from reporting.report_builder import build_report_envelope

def build_rollback_recommendation_report(environment: str, live_policy_version_id: str|None,
                                          rollback_watch_alerts: list[dict[str,Any]],
                                          metrics: dict[str,Any]) -> dict[str,Any]:
    return build_report_envelope("ROLLBACK_RECOMMENDATION_REPORT",environment,live_policy_version_id,
        "Rollback Recommendation Report",
        [{"title":"Rollback Watch Alerts","content":rollback_watch_alerts},
         {"title":"Current Metrics","content":metrics}],
        [f"Rollback-watch alerts: {len(rollback_watch_alerts)}",
         f"Live policy: {live_policy_version_id}",
         f"Fill score: {metrics.get('avg_fill_score_recent',0)}"])
