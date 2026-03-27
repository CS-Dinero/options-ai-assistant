"""stress/stress_report_builder.py — Builds structured stress memos."""
from __future__ import annotations
from typing import Any
from reporting.report_builder import build_report_envelope

def build_stress_report(environment: str, live_policy_version_id: str|None, scenario_name: str,
                         stressed_mandate: str, diff: dict[str,Any], resilience: dict[str,Any],
                         stressed_alerts: list[dict[str,Any]], stressed_refinements: list[dict[str,Any]]) -> dict[str,Any]:
    return build_report_envelope("STRESS_TEST_REPORT",environment,live_policy_version_id,
        f"Stress Test Report: {scenario_name}",
        [{"title":"Stress Diff","content":diff},{"title":"Resilience Score","content":resilience},
         {"title":"Top Alerts Under Stress","content":stressed_alerts[:10]},
         {"title":"Top Refinements Under Stress","content":stressed_refinements[:10]}],
        [f"Scenario: {scenario_name}",f"Mandate under stress: {stressed_mandate}",
         f"Resilience score: {resilience.get('resilience_score',0)} ({resilience.get('status')})",
         f"Queue depth Δ: {diff.get('queue_depth_delta')}",
         f"Blocked rate Δ: {diff.get('blocked_rate_delta')}",
         f"Alert count Δ: {diff.get('alert_count_delta')}"])
