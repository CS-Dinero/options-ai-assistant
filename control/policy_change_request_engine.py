"""control/policy_change_request_engine.py — Formal policy change proposals."""
from __future__ import annotations
from typing import Any
from datetime import datetime
import uuid

def create_policy_change_request(
    baseline_version_id: str, proposed_policy_bundle: dict[str,Any],
    scenario_name: str, diff_summary: dict[str,Any],
    requested_by: str="system", title: str="", reason: str="",
    risk_notes: list[str]|None=None) -> dict[str,Any]:
    return {"change_request_id":str(uuid.uuid4()),"baseline_version_id":baseline_version_id,
            "scenario_name":scenario_name,"title":title or scenario_name,
            "reason":reason,"requested_by":requested_by,
            "requested_utc":datetime.utcnow().isoformat(),
            "risk_notes":risk_notes or [],"diff_summary":diff_summary,
            "proposed_policy_bundle":proposed_policy_bundle,"state":"DRAFT"}
