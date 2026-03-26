"""control/policy_approval_engine.py — Moves change request to approved version."""
from __future__ import annotations
from typing import Any
from datetime import datetime
from control.policy_version_registry import create_policy_version

def approve_policy_change_request(change_request: dict[str,Any], approver: str,
                                   approval_note: str="") -> dict[str,Any]:
    v = create_policy_version(change_request["proposed_policy_bundle"], status="APPROVED",
                               parent_version_id=change_request.get("baseline_version_id"),
                               scenario_name=change_request.get("scenario_name"),
                               notes=approval_note)
    v["approved_utc"] = datetime.utcnow().isoformat()
    v["approved_by"] = approver
    return v
