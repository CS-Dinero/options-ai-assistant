"""meta/refinement_packet_builder.py — Creates structured refinement recommendation packets."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_refinement_packet(environment: str, candidate: dict[str,Any],
                             mapped_policy_change: dict[str,Any]) -> dict[str,Any]:
    return {"refinement_id":str(uuid.uuid4()),"environment":environment,
            "created_utc":datetime.utcnow().isoformat(),
            "signal_type":candidate.get("signal_type"),
            "target_type":candidate.get("target_type"),"target_id":candidate.get("target_id"),
            "refinement_type":candidate.get("refinement_type"),
            "refinement_score":candidate.get("refinement_score",0.0),
            "evidence_strength":candidate.get("evidence_strength",0.0),
            "safety_score":candidate.get("safety_score",0.0),
            "urgency_score":candidate.get("urgency_score",0.0),
            "evidence":candidate.get("evidence",{}),"proposed_change":candidate.get("proposed_change",{}),
            "policy_change_mapping":mapped_policy_change,
            "recommended_question":"Should this refinement become a formal policy simulation or change request?",
            "state":"OPEN"}
