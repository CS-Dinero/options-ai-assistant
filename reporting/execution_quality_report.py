"""reporting/execution_quality_report.py — Fill quality, slippage, execution analysis."""
from __future__ import annotations
from typing import Any
from reporting.report_builder import build_report_envelope

def build_execution_quality_report(environment: str, live_policy_version_id: str|None,
                                    slippage_model: dict[str,Any], metrics: dict[str,Any],
                                    hotspots: dict[str,Any]) -> dict[str,Any]:
    return build_report_envelope("EXECUTION_QUALITY_REPORT",environment,live_policy_version_id,
        "Execution Quality Report",
        [{"title":"By Symbol","content":slippage_model.get("by_symbol",{})},
         {"title":"By Window","content":slippage_model.get("by_window",{})},
         {"title":"By Policy","content":slippage_model.get("by_policy",{})},
         {"title":"Hotspots","content":hotspots}],
        [f"Fill score: {metrics.get('avg_fill_score_recent',0)}",
         f"Slippage: {metrics.get('avg_slippage_recent',0)}",
         f"Worst symbol: {hotspots.get('worst_symbol','N/A')}"])
