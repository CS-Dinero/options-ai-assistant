"""reporting/policy_impact_memo.py — Before/after analysis for a policy activation."""
from __future__ import annotations
from typing import Any
from reporting.report_builder import build_report_envelope

def build_policy_impact_memo(environment: str, live_policy_version_id: str,
                              impact_rows: list[dict[str,Any]],
                              refinements: list[dict[str,Any]]|None=None) -> dict[str,Any]:
    sections=[{"title":"Policy Impact","content":impact_rows}]
    if refinements:
        sections.append({"title":"Suggested Next Refinements","content":refinements[:3]})
    return build_report_envelope("POLICY_IMPACT_MEMO",environment,live_policy_version_id,
                                  "Policy Impact Memo",sections,
                                  [f"Policy: {live_policy_version_id}",
                                   f"Tracked metrics: {len(impact_rows)}"])
