"""review/review_resolution_engine.py — Resolves review tasks and creates decision packets."""
from __future__ import annotations
from typing import Any
from decision.decision_packet_builder import build_decision_packet
from decision.operator_rationale_engine import attach_operator_rationale

def resolve_review(review_task: dict[str,Any], decision_type: str, actor: str,
                   agreement_mode: str="AGREE", confidence: str="MEDIUM",
                   primary_reason_code: str="APPROVAL_CONFIDENCE_HIGH",
                   freeform_note: str="") -> tuple[dict[str,Any], dict[str,Any]]:
    updated_review=dict(review_task); updated_review["state"]="RESOLVED"
    dp=build_decision_packet(environment=review_task.get("environment","?"),
                              actor=actor,decision_type=decision_type,
                              source_object_id=review_task.get("object_id","?"),
                              source_object_type=review_task.get("review_type","?"),
                              review_id=review_task.get("review_id"))
    dp=attach_operator_rationale(dp,agreement_mode,confidence,primary_reason_code,
                                  freeform_note=freeform_note)
    return updated_review,dp
