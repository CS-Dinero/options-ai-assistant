"""compare/path_report_builder.py — Builds a structured comparative path memo."""
from __future__ import annotations
from typing import Any
from reporting.report_builder import build_report_envelope

def build_path_comparison_report(environment: str, live_policy_version_id: str|None,
                                  symbol: str, active_mandate: str,
                                  ranked_paths: list[dict[str,Any]]) -> dict[str,Any]:
    best=ranked_paths[0] if ranked_paths else {}
    return build_report_envelope("PATH_COMPARISON_REPORT",environment,live_policy_version_id,
        f"Path Comparison Report: {symbol}",
        [{"title":"Ranked Paths","content":ranked_paths}],
        [f"Symbol: {symbol}",f"Mandate: {active_mandate}",
         f"Top path: {best.get('path_code','N/A')}",
         f"Top path score: {best.get('path_total_score','N/A')}"])
