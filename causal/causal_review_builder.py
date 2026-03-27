"""causal/causal_review_builder.py — Builds causal review memos."""
from __future__ import annotations
from typing import Any
from reporting.report_builder import build_report_envelope

def build_causal_review(environment: str, live_policy_version_id: str|None,
                         intervention: dict[str,Any], before_after_summary: dict[str,Any],
                         effect_rows: list[dict[str,Any]], evidence_strength: dict[str,Any]) -> dict[str,Any]:
    return build_report_envelope("CAUSAL_REVIEW_REPORT",environment,live_policy_version_id,
        f"Causal Review: {intervention.get('title')}",
        [{"title":"Intervention","content":intervention},
         {"title":"Before / After Summary","content":before_after_summary},
         {"title":"Estimated Effects","content":effect_rows},
         {"title":"Evidence Strength","content":evidence_strength}],
        [f"Intervention: {intervention.get('title')}",
         f"Type: {intervention.get('intervention_type')}",
         f"Evidence: {evidence_strength.get('evidence_strength_label')} ({evidence_strength.get('evidence_strength_score')})"])
