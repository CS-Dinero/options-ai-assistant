"""meta/refinement_to_policy_request_engine.py — Converts approved refinement to policy change request."""
from __future__ import annotations
from typing import Any
from control.policy_change_request_engine import create_policy_change_request

def convert_refinement_to_change_request(refinement_packet: dict[str,Any],
                                          baseline_version_id: str,
                                          requested_by: str="system") -> dict[str,Any]:
    return create_policy_change_request(
        baseline_version_id=baseline_version_id,
        proposed_policy_bundle=refinement_packet.get("policy_change_mapping",{}),
        scenario_name=refinement_packet.get("refinement_type","REFINEMENT_REQUEST"),
        diff_summary={"source_refinement_id":refinement_packet.get("refinement_id"),
                      "signal_type":refinement_packet.get("signal_type"),
                      "target_id":refinement_packet.get("target_id")},
        requested_by=requested_by,
        title=f"Refinement: {refinement_packet.get('refinement_type')}",
        reason=refinement_packet.get("recommended_question",""),
        risk_notes=[f"Generated from refinement score {refinement_packet.get('refinement_score',0.0)}"])
