"""autopilot/action_classification_engine.py — Classifies concrete requests into action families."""
from __future__ import annotations
from typing import Any

ACTION_MAP: dict = {
    "build_queue":          "QUEUE_RANKING",
    "generate_report":      "REPORT_GENERATION",
    "generate_alerts":      "ALERT_GENERATION",
    "create_review":        "REVIEW_CREATION",
    "propose_refinement":   "REFINEMENT_SUGGESTION",
    "simulate_policy":      "POLICY_SIMULATION",
    "approve_policy":       "POLICY_APPROVAL",
    "activate_policy":      "POLICY_ACTIVATION",
    "compute_capital_size": "CAPITAL_SIZING",
    "draft_ticket":         "TICKET_DRAFTING",
    "execute_live":         "LIVE_EXECUTION",
    "propose_pruning":      "PRUNING_RECOMMENDATION",
    "rollout_release":      "RELEASE_ROLLOUT",
}

def classify_action_request(request: dict[str,Any]) -> str:
    return ACTION_MAP.get(request.get("action_type",""),"UNKNOWN")
