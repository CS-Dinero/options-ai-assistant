"""review/review_workflow_engine.py — Explicit lifecycle states for review tasks."""
from __future__ import annotations
from typing import Any

REVIEW_STATE_RULES: dict = {
    "OPEN":       {"IN_REVIEW","DISMISSED","ARCHIVED"},
    "IN_REVIEW":  {"RESOLVED","DISMISSED","ARCHIVED"},
    "RESOLVED":   {"ARCHIVED"},
    "DISMISSED":  {"ARCHIVED"},
    "ARCHIVED":   set(),
}

class InvalidReviewTransition(Exception):
    pass

def transition_review_state(packet: dict[str,Any], target_state: str) -> dict[str,Any]:
    current=packet.get("state","OPEN")
    if target_state not in REVIEW_STATE_RULES.get(current,set()):
        raise InvalidReviewTransition(f"Invalid: {current} → {target_state}")
    out=dict(packet); out["state"]=target_state; return out
