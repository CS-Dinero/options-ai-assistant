"""prune/pruning_recommendation_builder.py — Creates structured pruning recommendation packets."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def build_pruning_recommendation(environment: str, candidate: dict[str,Any],
                                  merge_candidates: list[dict[str,Any]]|None=None) -> dict[str,Any]:
    return {"pruning_recommendation_id":str(uuid.uuid4()),"environment":environment,
            "component_family":candidate.get("component_family"),
            "component_id":candidate.get("component_id"),
            "candidate_type":candidate.get("candidate_type"),
            "recommendation":candidate.get("recommendation"),
            "simplify_score":candidate.get("simplify_score",0),
            "blast_radius":candidate.get("blast_radius",0),
            "safety_to_change":candidate.get("safety_to_change",0),
            "reason":candidate.get("reason",""),"evidence":candidate.get("evidence",{}),
            "merge_candidates":merge_candidates or [],"state":"OPEN",
            "created_utc":datetime.utcnow().isoformat()}
