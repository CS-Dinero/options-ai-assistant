"""attribution/attribution_report_builder.py — Builds structured attribution reports."""
from __future__ import annotations
from typing import Any
from reporting.report_builder import build_report_envelope

def build_attribution_report(environment: str, live_policy_version_id: str|None,
                              playbook_attr: dict[str,Any], mandate_attr: dict[str,Any],
                              decision_attr: dict[str,Any], handoff_attr: dict[str,Any],
                              interactions: dict[str,Any]) -> dict[str,Any]:
    return build_report_envelope("ATTRIBUTION_REPORT",environment,live_policy_version_id,
        "Performance Attribution Report",
        [{"title":"Playbook Attribution","content":playbook_attr},
         {"title":"Mandate Attribution","content":mandate_attr},
         {"title":"Decision Attribution","content":decision_attr},
         {"title":"Handoff Attribution","content":handoff_attr},
         {"title":"Interaction Attribution","content":interactions}],
        [f"Playbooks tracked: {len(playbook_attr)}",f"Mandates tracked: {len(mandate_attr)}",
         f"Decisions tracked: {len(decision_attr)}",f"Handoffs tracked: {len(handoff_attr)}"])
