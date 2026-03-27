"""twin/twin_report_builder.py — Builds digital twin reports."""
from __future__ import annotations
from typing import Any
from reporting.report_builder import build_report_envelope

def build_twin_report(environment: str, live_policy_version_id: str|None,
                       decision_moment: dict[str,Any], reconciliation: dict[str,Any],
                       comparison: dict[str,Any]) -> dict[str,Any]:
    return build_report_envelope("DIGITAL_TWIN_REPORT",environment,live_policy_version_id,
        f"Digital Twin Report: {decision_moment.get('symbol')}",
        [{"title":"Decision Moment","content":decision_moment},
         {"title":"Reconciliation","content":reconciliation},
         {"title":"Chosen vs Counterfactual","content":comparison}],
        [f"Symbol: {decision_moment.get('symbol')}",
         f"Recommended: {reconciliation.get('recommended_path_code')}",
         f"Approved: {reconciliation.get('approved_path_code')}",
         f"Executed: {reconciliation.get('executed_path_code')}"])
