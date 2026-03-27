"""prune/pruning_to_review_engine.py — Routes high-impact pruning recommendations into review."""
from __future__ import annotations
from typing import Any
from review.review_trigger_engine import build_review_task

def convert_pruning_to_review(environment: str, recommendation: dict[str,Any]) -> dict[str,Any]:
    return build_review_task("POLICY_SIMULATION_REVIEW",environment,
                              recommendation.get("pruning_recommendation_id","?"),
                              f"Review pruning recommendation: {recommendation.get('component_id')} — {recommendation.get('reason','')}",
                              source=recommendation)
