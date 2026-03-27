"""review/review_assignment_engine.py — Routes review packets to correct role."""
from __future__ import annotations
from typing import Any

ROLE_MAP: dict = {
    "POLICY_CHANGE_APPROVAL_REVIEW": "APPROVER",
    "ROLLBACK_WATCH_REVIEW":         "APPROVER",
    "SLIPPAGE_HOTSPOT_REVIEW":       "TRADER_OPERATOR",
    "CAPITAL_CHOKE_REVIEW":          "APPROVER",
    "PROMOTED_PLAYBOOK_REVIEW":      "APPROVER",
    "QUEUE_STARVATION_REVIEW":       "ANALYST",
    "PLAYBOOK_DEGRADATION_REVIEW":   "ANALYST",
    "POLICY_SIMULATION_REVIEW":      "ANALYST",
}

def assign_review_role(packet: dict[str,Any]) -> dict[str,Any]:
    out=dict(packet); out["assigned_role"]=ROLE_MAP.get(packet.get("review_type",""),"ANALYST"); return out
