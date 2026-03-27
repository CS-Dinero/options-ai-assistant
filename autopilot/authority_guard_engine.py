"""autopilot/authority_guard_engine.py — Blocks over-delegation; the hard enforcement layer."""
from __future__ import annotations
from typing import Any
from autopilot.boundary_policy_engine import get_allowed_authority

AUTHORITY_ORDER: dict = {"AUTO":0,"AUTO_DRAFT":1,"HUMAN_APPROVAL":2,"HUMAN_EXECUTION":3,"NEVER_AUTOMATE":4}

def evaluate_authority_guard(environment: str, action_family: str,
                              requested_authority: str) -> dict[str,Any]:
    allowed=get_allowed_authority(environment,action_family)
    req_rank=AUTHORITY_ORDER.get(requested_authority,999)
    alw_rank=AUTHORITY_ORDER.get(allowed,999)
    ok=req_rank>=alw_rank
    return {"allowed":ok,"environment":environment,"action_family":action_family,
            "requested_authority":requested_authority,"maximum_allowed_authority":allowed,
            "reason":None if ok else f"{action_family} in {environment} may not exceed {allowed}"}
